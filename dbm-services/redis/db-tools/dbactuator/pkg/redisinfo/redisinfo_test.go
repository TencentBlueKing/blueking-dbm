package redisinfo

import (
	"fmt"
	"io/ioutil"
	"os"
	"testing"

	td "github.com/maxatome/go-testdeep"
	"github.com/stretchr/testify/assert"
)

func Test_Full(t *testing.T) {
	for _, file := range [2]string{"./resources/output.txt", "./resources/output_backslashr.txt"} {
		t.Run(fmt.Sprintf("testing file %s", file), func(tt *testing.T) {
			content, err := ioutil.ReadFile(file)
			assert.NoError(tt, err)
			_, err = Parse(string(content))
			assert.NoError(tt, err)
			/*td.CmpStruct(tt, info, Info{
				Server: Server{
					RedisVersion:    "3.2.5",
					RedisGitSha1:    "00000000",
					RedisGitDirty:   false,
					RedisBuildID:    "6f9920d2ae584aa0",
					RedisMode:       "standalone",
					OS:              "Linux 4.14.66-ovh-vps-grsec-zfs-classid x86_64",
					ArchBits:        64,
					MultiplexingAPI: "epoll",
					GCCVersion:      "4.9.2",
					ProcessID:       7,
					RunID:           "a4fcd0061e667352b73ad678f944d41b23c9c67a",
					TCPPort:         6379,
					UptimeInDays:    24,
					UptimeInSeconds: 2089968,
					HZ:              10,
					LRUClock:        1870516,
					Executable:      "/data/redis-server",
					ConfigFile:      "/redis.conf",
				},
				Clients: Client{
					ConnectedClients:        914,
					ClientLongestOutputList: 0,
					ClientBiggestInputBuf:   0,
					BlockedClients:          20,
				},
				Memory: Memory{
					UsedMemory:             6146978688,
					UsedMemoryHuman:        "5.72G",
					UsedMemoryRss:          6454341632,
					UsedMemoryRssHuman:     "6.01G",
					UsedMemoryPeak:         6290131040,
					UsedMemoryPeakHuman:    "5.86G",
					TotalSystemMemory:      135210360832,
					TotalSystemMemoryHuman: "125.92G",
					UsedMemoryLua:          37888,
					UsedMemoryLuaHuman:     "37.00K",
					Maxmemory:              0,
					MaxmemoryHuman:         "0B",
					MaxmemoryPolicy:        "noeviction",
					MemFragmentationRatio:  1.05,
					MemAllocator:           "jemalloc-4.0.3",
				},
				Persistence: Persistence{
					Loading:                  false,
					RdbChangesSinceLastSave:  9629911,
					RdbBgsaveInProgress:      false,
					RdbLastSaveTime:          1578891904,
					RdbLastBgsaveStatus:      "ok",
					RdbLastBgsaveTimeSec:     19,
					RdbCurrentBgsaveTimeSec:  -1,
					AofEnabled:               false,
					AofRewriteInProgress:     false,
					AofRewriteScheduled:      false,
					AofCurrentRewriteTimeSec: -1,
					AofLastRewriteTimeSec:    -1,
					AofLastBgrewriteStatus:   "ok",
					AofLastWriteStatus:       "ok",
				},
				Stats: Stats{
					TotalConnectionsReceived: 1209273,
					TotalCommandsProcessed:   1322487410,
					InstantaneousOpsPerSec:   448,
					TotalNetInputBytes:       498224475818,
					TotalNetOutputBytes:      3210532894008,
					InstantaneousInputKbps:   125.06,
					InstantaneousOutputKbps:  601.62,
					RejectedConnections:      0,
					SyncFull:                 53,
					SyncPartialOk:            77,
					SyncPartialErr:           4,
					ExpiredKeys:              24052947,
					EvictedKeys:              0,
					KeyspaceHits:             227762505,
					KeyspaceMisses:           8586015,
					PubsubChannels:           20373,
					PubsubPatterns:           40,
					LatestForkUsec:           189282,
					MigrateCachedSockets:     false,
				},
				Replication: Replication{
					Role:            "master",
					ConnectedSlaves: 3,
					Slaves: []ReplicationSlave{
						{
							ID:     0,
							IP:     "127.0.0.1",
							Port:   31000,
							State:  "online",
							Offset: 222662780961,
							Lag:    0,
						},
						{
							ID:     1,
							IP:     "127.0.0.1",
							Port:   31003,
							State:  "online",
							Offset: 222662776891,
							Lag:    0,
						},
						{
							ID:     2,
							IP:     "127.0.0.1",
							Port:   31001,
							State:  "online",
							Offset: 222662775148,
							Lag:    0,
						},
					},
					MasterReplOffset:           222662781103,
					ReplBacklogActive:          true,
					ReplBacklogSize:            1048576,
					ReplBacklogFirstByteOffset: 222661732528,
					ReplBacklogHistLen:         1048576,
				},
				CPU: CPU{
					UsedCPUSys:          44232.89,
					UsedCPUUser:         16130.08,
					UsedCPUSysChildren:  29.10,
					UsedCPUUserChildren: 259.26,
				},
				Cluster: Cluster{
					ClusterEnabled: false,
				},
				Keyspace: []Keyspace{
					{
						DB:      1,
						Keys:    58,
						Expires: 0,
						AvgTTL:  0,
					},
					{
						DB:      3,
						Keys:    307122,
						Expires: 307122,
						AvgTTL:  5549135,
					},
					{
						DB:      4,
						Keys:    6,
						Expires: 6,
						AvgTTL:  88504,
					},
					{
						DB:      6,
						Keys:    10453,
						Expires: 0,
						AvgTTL:  0,
					},
					{
						DB:      7,
						Keys:    7,
						Expires: 5,
						AvgTTL:  133782010,
					},
					{
						DB:      11,
						Keys:    32,
						Expires: 32,
						AvgTTL:  137917,
					},
					{
						DB:      12,
						Keys:    38,
						Expires: 38,
						AvgTTL:  115430,
					},
					{
						DB:      13,
						Keys:    98863,
						Expires: 98863,
						AvgTTL:  85569597,
					},
				},
			}, td.StructFields{}, "got correct structure")*/
		})
	}
}

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
			UsedMemory:            81239824,
			UsedMemoryHuman:       "77.48M",
			UsedMemoryRss:         82206720,
			UsedMemoryRssHuman:    "78.40M",
			UsedMemoryPeak:        81629784,
			UsedMemoryPeakHuman:   "77.85M",
			UsedMemoryLua:         31744,
			UsedMemoryLuaHuman:    "31.00K",
			MemFragmentationRatio: 1.01,
			MemAllocator:          "jemalloc-5.2.1",
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
	fmt.Printf("%s", info.Server.RedisVersion)
	assert.Equal(t, info.Server.RedisVersion, "2.7.4-rocksdb-v8.5.3")
	assert.NoError(t, err)
}
