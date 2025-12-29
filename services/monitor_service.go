//go:build windows

package services

import (
	"bufio"
	"context"
	"encoding/json"
	"errors"
	"io"
	"log"
	"os/exec"
	"sync"
	"syscall"
	"time"
)

// SystemInfo matches the structure of the JSON output from VortSensors.exe
type SystemInfo struct {
	CPU     CPUInfo     `json:"cpu"`
	GPU     GPUInfo     `json:"gpu"`
	RAM     RAMInfo     `json:"ram"`
	Battery BatteryInfo `json:"battery"`
}

type CPUInfo struct {
	Name         string  `json:"name"`
	PackageTemp  float32 `json:"packageTemp"`
	TotalLoad    float32 `json:"totalLoad"`
	PackagePower float32 `json:"packagePower"`
}

type GPUInfo struct {
	Name        string  `json:"name"`
	Temp        float32 `json:"temp"`
	Load        float32 `json:"load"`
	MemoryUsed  float32 `json:"memoryUsed"`
	MemoryTotal float32 `json:"memoryTotal"`
}

type RAMInfo struct {
	Used      float32 `json:"used"`
	Available float32 `json:"available"`
	Total     float32 `json:"total"`
}

type BatteryInfo struct {
	ChargeLevel float32 `json:"chargeLevel"`
	Voltage     float32 `json:"voltage"`
	WearLevel   float32 `json:"wearLevel"`
}

type MonitorService struct {
	ctx         context.Context
	cancel      context.CancelFunc
	OnData      func(info SystemInfo)
	OnError     func(err error)
	sidecarPath string
	cmd         *exec.Cmd
	mutex       sync.Mutex
}

func NewMonitorService(sidecarPath string) *MonitorService {
	return &MonitorService{
		sidecarPath: sidecarPath,
	}
}

func (s *MonitorService) Start() {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	if s.cancel != nil {
		s.cancel()
	}
	s.ctx, s.cancel = context.WithCancel(context.Background())

	go s.runSidecar()
}

func (s *MonitorService) Stop() {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	if s.cancel != nil {
		s.cancel()
	}
	if s.cmd != nil && s.cmd.Process != nil {
		s.cmd.Process.Kill()
	}
}

func (s *MonitorService) runSidecar() {
	const maxRetries = 2
	const retryDelay = 2 * time.Second

	for i := 0; ; i++ {
		select {
		case <-s.ctx.Done():
			return
		default:
		}

		if i > 0 {
			time.Sleep(retryDelay)
		}

		log.Printf("Starting VortSensors.exe (attempt %d)...", i+1)

		s.cmd = exec.CommandContext(s.ctx, s.sidecarPath)
		s.cmd.SysProcAttr = &syscall.SysProcAttr{
			HideWindow:    true,
			CreationFlags: 0x08000000, // CREATE_NO_WINDOW
		}

		stdout, err := s.cmd.StdoutPipe()
		if err != nil {
			log.Printf("Error creating stdout pipe: %v", err)
			continue
		}

		// Use a separate goroutine to read from stdout to prevent blocking
		var wg sync.WaitGroup
		wg.Add(1)
		go func() {
			defer wg.Done()
			s.readOutput(stdout)
		}()

		if err := s.cmd.Start(); err != nil {
			log.Printf("Error starting VortSensors.exe: %v", err)
			continue
		}

		err = s.cmd.Wait()
		wg.Wait() // Wait for the reader to finish

		log.Printf("VortSensors.exe exited with error: %v", err)

		if i >= maxRetries-1 {
			log.Println("Sidecar failed to start after multiple retries. Falling back.")
			if s.OnError != nil {
				s.OnError(errors.New("sidecar failed to start"))
			}
			return // Stop trying
		}
	}
}

func (s *MonitorService) readOutput(stdout io.ReadCloser) {
	scanner := bufio.NewScanner(stdout)
	for scanner.Scan() {
		select {
		case <-s.ctx.Done():
			return // Stop reading if the service is stopped
		default:
			var info SystemInfo
			if err := json.Unmarshal(scanner.Bytes(), &info); err == nil {
				if s.OnData != nil {
					s.OnData(info)
				}
			} else {
				// Avoid logging parsing errors for empty or malformed lines
				if len(scanner.Bytes()) > 0 {
					log.Printf("Error parsing JSON from sidecar: %v", err)
				}
			}
		}
	}
	if err := scanner.Err(); err != nil {
		// Don't log "read/write on closed pipe" error, it's expected on shutdown
		if !errors.Is(err, io.ErrClosedPipe) && !strings.Contains(err.Error(), "read/write on closed pipe") {
			log.Printf("Error reading from sidecar stdout: %v", err)
		}
	}
}
