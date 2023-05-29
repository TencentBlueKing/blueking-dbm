package logger

import (
	"os"

	"go.uber.org/zap"
)

var (
	// Skip TODO
	Skip = zap.Skip
	// Binary TODO
	Binary = zap.Binary
	// Bool TODO
	Bool = zap.Bool
	// Boolp TODO
	Boolp = zap.Boolp
	// ByteString TODO
	ByteString = zap.ByteString
	// Complex128 TODO
	Complex128 = zap.Complex128
	// Complex128p TODO
	Complex128p = zap.Complex128p
	// Complex64 TODO
	Complex64 = zap.Complex64
	// Complex64p TODO
	Complex64p = zap.Complex64p
	// Float64 TODO
	Float64 = zap.Float64
	// Float64p TODO
	Float64p = zap.Float64p
	// Float32 TODO
	Float32 = zap.Float32
	// Float32p TODO
	Float32p = zap.Float32p
	// Int TODO
	Int = zap.Int
	// Intp TODO
	Intp = zap.Intp
	// Int64 TODO
	Int64 = zap.Int64
	// Int64p TODO
	Int64p = zap.Int64p
	// Int32 TODO
	Int32 = zap.Int32
	// Int32p TODO
	Int32p = zap.Int32p
	// Int16 TODO
	Int16 = zap.Int16
	// Int16p TODO
	Int16p = zap.Int16p
	// Int8 TODO
	Int8 = zap.Int8
	// Int8p TODO
	Int8p = zap.Int8p
	// String TODO
	String = zap.String
	// Stringp TODO
	Stringp = zap.Stringp
	// Uint TODO
	Uint = zap.Uint
	// Uintp TODO
	Uintp = zap.Uintp
	// Uint64 TODO
	Uint64 = zap.Uint64
	// Uint64p TODO
	Uint64p = zap.Uint64p
	// Uint32 TODO
	Uint32 = zap.Uint32
	// Uint32p TODO
	Uint32p = zap.Uint32p
	// Uint16 TODO
	Uint16 = zap.Uint16
	// Uint16p TODO
	Uint16p = zap.Uint16p
	// Uint8 TODO
	Uint8 = zap.Uint8
	// Uint8p TODO
	Uint8p = zap.Uint8p
	// Uintptr TODO
	Uintptr = zap.Uintptr
	// Uintptrp TODO
	Uintptrp = zap.Uintptrp
	// Reflect TODO
	Reflect = zap.Reflect
	// Namespace TODO
	Namespace = zap.Namespace
	// Stringer TODO
	Stringer = zap.Stringer
	// Time TODO
	Time = zap.Time
	// Timep TODO
	Timep = zap.Timep
	// Stack TODO
	Stack = zap.Stack
	// StackSkip TODO
	StackSkip = zap.StackSkip
	// Duration TODO
	Duration = zap.Duration
	// Durationp TODO
	Durationp = zap.Durationp
	// Any TODO
	Any = zap.Any

	// Info TODO
	Info = std.Info
	// Warn TODO
	Warn = std.Warn
	// Error TODO
	Error = std.Error
	// DPanic TODO
	DPanic = std.DPanic
	// Panic TODO
	Panic = std.Panic
	// Fatal TODO
	Fatal = std.Fatal
	// Debug TODO
	Debug = std.Debug

	// Local TODO
	Local = std.Local
)

var std = New(os.Stderr, false, InfoLevel)

// Default TODO
func Default() *Logger {
	return std
}

// ResetDefault TODO
func ResetDefault(l *Logger) {
	std = l
	Info = std.Info
	Warn = std.Warn
	Error = std.Error
	DPanic = std.DPanic
	Panic = std.Panic
	Fatal = std.Fatal
	Debug = std.Debug
	Local = std.Local
}

// Sync TODO
func Sync() error {
	if std != nil {
		return std.Sync()
	}
	return nil
}
