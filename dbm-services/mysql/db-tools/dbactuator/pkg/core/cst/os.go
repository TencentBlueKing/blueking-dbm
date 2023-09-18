package cst

// bits
const (
	Bit64  = "64"
	Bit32  = "32"
	OSBits = 32 << uintptr(^uintptr(0)>>63)
)
