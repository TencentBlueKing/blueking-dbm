package redisinfo

import (
	"os"
	"testing"

	td "github.com/maxatome/go-testdeep"
	"github.com/stretchr/testify/assert"
)

func Test_OnlyServer(t *testing.T) {
	content, err := os.ReadFile("./resources/redis-5.0.8.txt")
	assert.NoError(t, err)
	info, err := Parse(string(content))
	assert.NoError(t, err)
	td.CmpStruct(t, info, Info{
		Server: Server{
			RedisVersion:    "5.0.8",
			RedisGitSha1:    "00000000",
			RedisGitDirty:   false,
			RedisBuildID:    "825de4a1bc818e9d",
			RedisMode:       "standalone",
			OS:              "Linux 5.4.241-1-tlinux4-0017.7 x86_64",
			ArchBits:        64,
			MultiplexingAPI: "epoll",
			GCCVersion:      "4.8.5",
			ProcessID:       217730,
			RunID:           "d6c5c2e644908042d059405f6e87e7c3cf714ddf",
			TCPPort:         6380,
			UptimeInDays:    64,
			UptimeInSeconds: 5607149,
			HZ:              10,
			LRUClock:        16135121,
			Executable:      "/data/redis/./redis-server",
			ConfigFile:      "/data/redis/6380/redis.conf",
		},
	}, td.StructFields{}, "got correct structure")
}
func Test_Memory28(t *testing.T) {
	content, err := os.ReadFile("./resources/info-memory.txt")
	assert.NoError(t, err)
	info, err := Parse(string(content))
	assert.NoError(t, err)
	td.CmpStruct(t, info, Info{
		Memory: Memory{
			UsedMemory:            55347544,
			UsedMemoryHuman:       "52.78M",
			UsedMemoryRss:         49123328,
			UsedMemoryRssHuman:    "",
			UsedMemoryPeak:        55939360,
			UsedMemoryPeakHuman:   "53.35M",
			UsedMemoryLua:         33792,
			MemFragmentationRatio: 0.89,
			MemAllocator:          "jemalloc-3.6.0",
		},
	}, td.StructFields{}, "got correct structure")
}
func Test_Info_7(t *testing.T) {
	content, err := os.ReadFile("./resources/info-7.0.7.txt")
	assert.NoError(t, err)
	info, err := Parse(string(content))
	assert.NoError(t, err)
	td.CmpStruct(t, info, Info{
		Memory: Memory{
			TotalSystemMemory:      67212910592,
			TotalSystemMemoryHuman: "62.60G",
			UsedMemory:             81239824,
			UsedMemoryHuman:        "77.48M",
			UsedMemoryRss:          82206720,
			UsedMemoryRssHuman:     "78.40M",
			UsedMemoryPeak:         81629784,
			UsedMemoryPeakHuman:    "77.85M",
			UsedMemoryLua:          31744,
			UsedMemoryLuaHuman:     "31.00K",
			MemFragmentationRatio:  1.01,
			MemAllocator:           "jemalloc-5.2.1",
			Maxmemory:              3865051136,
			MaxmemoryHuman:         "3.60G",
			MaxmemoryPolicy:        "noeviction",
		},
	}, td.StructFields{}, "got correct structure")
}

func Test_Info_5(t *testing.T) {
	content, err := os.ReadFile("./resources/redis-5.0.8.txt")
	assert.NoError(t, err)
	info, err := Parse(string(content))
	assert.NoError(t, err)
	assert.Equal(t, info.Server.RedisVersion, "5.0.8")

}

func Test_Info_TendisPlus(t *testing.T) {
	content, err := os.ReadFile("./resources/tendisplus-2.7.4-info.txt")
	assert.NoError(t, err)
	info, err := Parse(string(content))
	assert.NoError(t, err)
	assert.Equal(t, len(info.Replication.Slaves), 1)
	assert.Equal(t, info.Replication.Slaves[0].IP, "1.1.1.1")
	assert.Equal(t, info.Replication.Slaves[0].Port, uint16(30000))
	assert.Equal(t, info.Replication.Slaves[0].State, "online")
	assert.Equal(t, info.Replication.Slaves[0].Offset, int64(8227470964))
	assert.Equal(t, info.Replication.Slaves[0].Lag, int64(0))
	assert.Equal(t, info.Server.RedisVersion, "2.7.4-rocksdb-v8.5.3")
	assert.NoError(t, err)
}
