using System;
using System.Linq;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using LibreHardwareMonitor.Hardware;

public class UpdateVisitor : IVisitor
{
    public void VisitComputer(IComputer computer)
    {
        computer.Traverse(this);
    }
    public void VisitHardware(IHardware hardware)
    {
        hardware.Update();
        foreach (IHardware subHardware in hardware.SubHardware) subHardware.Accept(this);
    }
    public void VisitSensor(ISensor sensor) { }
    public void VisitParameter(IParameter parameter) { }
}

public class SystemInfo
{
    public CpuInfo? Cpu { get; set; }
    public GpuInfo? Gpu { get; set; }
    public RamInfo? Ram { get; set; }
    public BatteryInfo? Battery { get; set; }
}

public class CpuInfo
{
    public string? Name { get; set; }
    public float? PackageTemp { get; set; }
    public float? TotalLoad { get; set; }
    public float? PackagePower { get; set; }
}

public class GpuInfo
{
    public string? Name { get; set; }
    public float? Temp { get; set; }
    public float? Load { get; set; }
    public float? MemoryUsed { get; set; }
    public float? MemoryTotal { get; set; }
}

public class RamInfo
{
    public float? Used { get; set; }
    public float? Available { get; set; }
    public float? Total { get; set; }
}

public class BatteryInfo
{
    public float? ChargeLevel { get; set; }
    public float? Voltage { get; set; }
    public float? WearLevel { get; set; }
}

public class Program
{
    public static async Task Main(string[] args)
    {
        var computer = new Computer
        {
            IsCpuEnabled = true,
            IsGpuEnabled = true,
            IsMemoryEnabled = true,
            IsMotherboardEnabled = true,
            IsStorageEnabled = true,
            IsBatteryEnabled = true
        };

        computer.Open();
        computer.Accept(new UpdateVisitor());

        var cancellationTokenSource = new CancellationTokenSource();

        // Graceful shutdown on parent process exit
        var watchParentTask = Task.Run(() =>
        {
            try
            {
                // Reading from Console.In will block until the parent process closes the pipe.
                Console.In.Read();
                cancellationTokenSource.Cancel();
            }
            catch { /* Ignore exceptions on read, which can happen during shutdown */ }
        });

        JsonSerializerOptions jsonOptions = new JsonSerializerOptions
        {
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
            DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull
        };

        try
        {
            while (!cancellationTokenSource.IsCancellationRequested)
            {
                computer.Accept(new UpdateVisitor());

                var systemInfo = new SystemInfo
                {
                    Cpu = GetCpuInfo(computer),
                    Gpu = GetGpuInfo(computer),
                    Ram = GetRamInfo(computer),
                    Battery = GetBatteryInfo(computer)
                };

                string json = JsonSerializer.Serialize(systemInfo, jsonOptions);
                Console.WriteLine(json);

                await Task.Delay(1000, cancellationTokenSource.Token);
            }
        }
        catch (TaskCanceledException)
        {
            // This is expected on graceful shutdown.
        }
        finally
        {
            computer.Close();
        }
    }

    private static CpuInfo? GetCpuInfo(IComputer computer)
    {
        var cpu = computer.Hardware.FirstOrDefault(h => h.HardwareType == HardwareType.Cpu);
        if (cpu == null) return null;

        return new CpuInfo
        {
            Name = cpu.Name,
            PackageTemp = cpu.Sensors.FirstOrDefault(s => s.SensorType == SensorType.Temperature && s.Name.Contains("Package"))?.Value,
            TotalLoad = cpu.Sensors.FirstOrDefault(s => s.SensorType == SensorType.Load && s.Name.Contains("Total"))?.Value,
            PackagePower = cpu.Sensors.FirstOrDefault(s => s.SensorType == SensorType.Power && s.Name.Contains("Package"))?.Value
        };
    }

    private static GpuInfo? GetGpuInfo(IComputer computer)
    {
        var gpu = computer.Hardware.FirstOrDefault(h => h.HardwareType == HardwareType.GpuAmd || h.HardwareType == HardwareType.GpuNvidia);
        if (gpu == null) return null;

        return new GpuInfo
        {
            Name = gpu.Name,
            Temp = gpu.Sensors.FirstOrDefault(s => s.SensorType == SensorType.Temperature && s.Name.Contains("Core"))?.Value,
            Load = gpu.Sensors.FirstOrDefault(s => s.SensorType == SensorType.Load && s.Name.Contains("Core"))?.Value,
            MemoryUsed = gpu.Sensors.FirstOrDefault(s => s.SensorType == SensorType.SmallData && s.Name.Contains("Memory Used"))?.Value / 1024, // to GB
            MemoryTotal = gpu.Sensors.FirstOrDefault(s => s.SensorType == SensorType.SmallData && s.Name.Contains("Memory Total"))?.Value / 1024 // to GB
        };
    }

    private static RamInfo? GetRamInfo(IComputer computer)
    {
        var memory = computer.Hardware.FirstOrDefault(h => h.HardwareType == HardwareType.Memory);
        if (memory == null) return null;

        var used = memory.Sensors.FirstOrDefault(s => s.SensorType == SensorType.Data && s.Name == "Memory Used")?.Value;
        var available = memory.Sensors.FirstOrDefault(s => s.SensorType == SensorType.Data && s.Name == "Memory Available")?.Value;

        return new RamInfo
        {
            Used = used,
            Available = available,
            Total = (used.HasValue && available.HasValue) ? used + available : null
        };
    }

    private static BatteryInfo? GetBatteryInfo(IComputer computer)
    {
        var battery = computer.Hardware.FirstOrDefault(h => h.HardwareType == HardwareType.Battery);
        if (battery == null) return null;

        return new BatteryInfo
        {
            ChargeLevel = battery.Sensors.FirstOrDefault(s => s.SensorType == SensorType.Level && s.Name == "Charge Level")?.Value,
            Voltage = battery.Sensors.FirstOrDefault(s => s.SensorType == SensorType.Voltage)?.Value,
            WearLevel = battery.Sensors.FirstOrDefault(s => s.SensorType == SensorType.Level && s.Name == "Wear Level")?.Value,
        };
    }
}
