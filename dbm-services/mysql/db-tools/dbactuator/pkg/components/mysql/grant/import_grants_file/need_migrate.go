package import_grants_file

// 理论上是可以允许 MySQL, spider 混合克隆的
// 只要正确识别版本就行了
func (c *ImportGrantsFile) needMigrate() bool {
	if c.Params.MachineType == "spider" {
		// spider 1 == 55
		// spider 3 == 57
		// spider 4 == 80
		if c.sourceMajorVersion < 3000006 && c.destMajorVersion > 3000006 {
			return true
		}
	} else {
		if c.sourceMajorVersion < 5007000 && c.destMajorVersion > 5007000 {
			return true
		}
	}
	return false
}
