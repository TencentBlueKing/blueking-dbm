package disk

import (
	"fmt"
	"golang.org/x/sys/unix"
	"syscall"
)

// GetInfo returns total and free bytes available in a directory, e.g. `/`.
func GetInfo(path string) (info Info, err error) {
	s := syscall.Statfs_t{}

	err = syscall.Statfs(path, &s)
	if err != nil {
		return Info{}, err
	}

	reservedBlocks := s.Bfree - s.Bavail
	info = Info{
		Total: uint64(s.Bsize) * (s.Blocks - reservedBlocks),
		Free:  uint64(s.Bsize) * s.Bavail,
		Files: s.Files,
		Ffree: s.Ffree,
		//nolint:unconvert
		// FSType: getFSType(int64(s.Type)),
	}
	// Check for overflows.
	// https://github.com/minio/minio/issues/8035
	// XFS can show wrong values at times error out
	// in such scenarios.
	if info.Free > info.Total {
		return info, fmt.Errorf(
			"detected free space (%d) > total drive space (%d), fs corruption at (%s). please run 'fsck'",
			info.Free, info.Total, path)
	}
	info.Used = info.Total - info.Free

	st := syscall.Stat_t{}
	err = syscall.Stat(path, &st)
	if err != nil {
		return Info{}, err
	}
	//nolint:unconvert
	devID := uint64(st.Dev) // Needed to support multiple GOARCHs
	info.Major = unix.Major(devID)
	info.Minor = unix.Minor(devID)
	return info, nil
}
