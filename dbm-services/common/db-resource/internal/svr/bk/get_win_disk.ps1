$diskInfo = Get-WmiObject -Class Win32_LogicalDisk -Filter "DriveType=3" | ForEach-Object {
    [PSCustomObject]@{
        DriveLetter = $_.DeviceID
        TotalSize   = $_.Size
    }
}


$cpuInfo = (Get-WmiObject -Class Win32_Processor).NumberOfCores

$memoryInfo = (Get-WmiObject -Class Win32_OperatingSystem).TotalVisibleMemorySize

$systemInfo = [PSCustomObject]@{
    cpu = $cpuInfo
    mem = $memoryInfo
    disk = $diskInfo
}

$systemInfoJson = $systemInfo | ConvertTo-Json

$systemInfoJson

