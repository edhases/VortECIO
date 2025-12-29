//go:build windows

package sensors

import (
	"fmt"
	"github.com/go-ole/go-ole"
	"github.com/go-ole/go-ole/oleutil"
	"log"
)

// GetSystemModel retrieves the computer model from WMI (Win32_ComputerSystem).
// This is used for a safety check against the loaded XML configuration.
func GetSystemModel() (string, error) {
	ole.CoInitialize(0)
	defer ole.CoUninitialize()

	unknown, err := oleutil.CreateObject("WbemScripting.SWbemLocator")
	if err != nil {
		return "", err
	}
	defer unknown.Release()

	wmi, err := unknown.QueryInterface(ole.IID_IDispatch)
	if err != nil {
		return "", err
	}
	defer wmi.Release()

	serviceRaw, err := oleutil.CallMethod(wmi, "ConnectServer", nil, `\\.\root\cimv2`)
	if err != nil {
		return "", err
	}
	service := serviceRaw.ToIDispatch()
	defer service.Release()

	resultRaw, err := oleutil.CallMethod(service, "ExecQuery", "SELECT * FROM Win32_ComputerSystem")
	if err != nil {
		return "", err
	}
	result := resultRaw.ToIDispatch()
	defer result.Release()

	countVariant, err := oleutil.GetProperty(result, "Count")
	if err != nil {
		return "", err
	}
	count := int(countVariant.Val)

	if count == 0 {
		return "", fmt.Errorf("no Win32_ComputerSystem instance found")
	}

	itemRaw, err := oleutil.CallMethod(result, "ItemIndex", 0)
	if err != nil {
		return "", err
	}
	item := itemRaw.ToIDispatch()
	defer item.Release()

	modelVariant, err := oleutil.GetProperty(item, "Model")
	if err != nil {
		return "", err
	}

	log.Printf("Detected system model: %s", modelVariant.ToString())
	return modelVariant.ToString(), nil
}
