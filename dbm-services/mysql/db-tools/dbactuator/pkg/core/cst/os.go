package cst

import "strconv"

// bits
const (
	// X64 x86_64
	X64 = "x86_64"
	// X32 x86_32
	X32 = "i686"
	// Arm64 aarch64
	Arm64 = "aarch64"
	Bit64 = 64
	Bit32 = 32
	//OSBits = 32 << uintptr(^uintptr(0)>>63)
	OSBits = strconv.IntSize
)
