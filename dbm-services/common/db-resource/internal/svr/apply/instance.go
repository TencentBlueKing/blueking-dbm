package apply

// InstanceObject TODO
type InstanceObject struct {
	BkHostId        int
	Equipment       string
	LinkNetdeviceId []string
	Nice            int64
}

// GetLinkNetDeviceIdsInterface TODO
func (c *InstanceObject) GetLinkNetDeviceIdsInterface() []interface{} {
	var k []interface{}
	for _, v := range c.LinkNetdeviceId {
		k = append(k, v)
	}
	return k
}

// Wrapper TODO
type Wrapper struct {
	Instances []InstanceObject
	by        func(p, q *InstanceObject) bool
}

// SortBy TODO
type SortBy func(p, q *InstanceObject) bool

// Len 用于排序
func (pw Wrapper) Len() int { // 重写 Len() 方法
	return len(pw.Instances)
}

// Swap 用于排序
func (pw Wrapper) Swap(i, j int) { // 重写 Swap() 方法
	pw.Instances[i], pw.Instances[j] = pw.Instances[j], pw.Instances[i]
}

// Less 用于排序
func (pw Wrapper) Less(i, j int) bool { // 重写 Less() 方法
	return pw.by(&pw.Instances[i], &pw.Instances[j])
}
