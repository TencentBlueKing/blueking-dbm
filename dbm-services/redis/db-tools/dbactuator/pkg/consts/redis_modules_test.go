package consts

import (
	"reflect"
	"strings"
	"testing"
)

func TestModuleCommandItems(t *testing.T) {
	tests := []struct {
		name string
		got  []RedisModuleCmdItem
		want []RedisModuleCmdItem
	}{
		{
			name: "fo4 lock",
			got:  Fo4LockCmdItems,
			want: []RedisModuleCmdItem{
				{Command: "REDIS_LOCK.ACQUIRE", Mode: ModeWrite, MinArgs: 4, MaxArgs: 4},
				{Command: "REDIS_LOCK.RELEASE", Mode: ModeWrite, MinArgs: 3, MaxArgs: 3},
			},
		},
		{
			name: "fo4 util",
			got:  Fo4UtilCmdItems,
			want: []RedisModuleCmdItem{
				{Command: "REDIS_UTIL.SAFEHINCRBY", MinArgs: 4, MaxArgs: 4},
				{Command: "REDIS_UTIL.HINCRCLAMP", MinArgs: 6, MaxArgs: 6},
				{Command: "REDIS_UTIL.HMSETNX", MinArgs: 4, MaxArgs: 9999},
				{Command: "REDIS_UTIL.CLAMP", Mode: ModeWrite, MinArgs: 4, MaxArgs: 4},
				{Command: "REDIS_UTIL.INCRCLAMP", Mode: ModeWrite, MinArgs: 5, MaxArgs: 5},
				{Command: "REDIS_UTIL.DECRCLAMP", Mode: ModeWrite, MinArgs: 5, MaxArgs: 5},
			},
		},
		{
			name: "redis cell",
			got:  RedisCellCmdItems,
			want: []RedisModuleCmdItem{
				{Command: "CL.THROTTLE", Mode: ModeWrite, MinArgs: 5, MaxArgs: 6},
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if !reflect.DeepEqual(tt.got, tt.want) {
				t.Errorf("command items = %#v, want %#v", tt.got, tt.want)
			}
		})
	}
}

func TestGetPredixyModuleCommandsExactContent(t *testing.T) {
	want := `
CustomCommand {
	
    redis_util.safehincrby {
		MinArgs 4
		MaxArgs 4
	}
	
    redis_util.hincrclamp {
		MinArgs 6
		MaxArgs 6
	}
	
    redis_util.hmsetnx {
		MinArgs 4
		MaxArgs 9999
	}
	
    redis_util.clamp {
		Mode write
		MinArgs 4
		MaxArgs 4
	}
	
    redis_util.incrclamp {
		Mode write
		MinArgs 5
		MaxArgs 5
	}
	
    redis_util.decrclamp {
		Mode write
		MinArgs 5
		MaxArgs 5
	}
	
    redis_lock.acquire {
		Mode write
		MinArgs 4
		MaxArgs 4
	}
	
    redis_lock.release {
		Mode write
		MinArgs 3
		MaxArgs 3
	}
	
    cl.throttle {
		Mode write
		MinArgs 5
		MaxArgs 6
	}
	
}
	`
	got := GetPredixyModuleCommands([]string{ModuleFo4Util, ModuleFo4Lock, ModuleRedisCell})
	if got != want {
		t.Errorf("GetPredixyModuleCommands() content mismatch\ngot:\n%q\nwant:\n%q", got, want)
	}
}

func TestGetFirstCommandByModule(t *testing.T) {
	tests := []struct {
		module string
		want   string
	}{
		{module: ModuleFo4Lock, want: "REDIS_LOCK.ACQUIRE"},
		{module: ModuleFo4Util, want: "REDIS_UTIL.SAFEHINCRBY"},
		{module: ModuleRedisCell, want: "CL.THROTTLE"},
	}

	for _, tt := range tests {
		t.Run(tt.module, func(t *testing.T) {
			if got := GetFirstCommandByModule(tt.module); got != tt.want {
				t.Errorf("GetFirstCommandByModule(%q) = %q, want %q", tt.module, got, tt.want)
			}
		})
	}
}

func TestRedisModuleCmdItemToStringOmitsEmptyMode(t *testing.T) {
	item := RedisModuleCmdItem{
		Command: "REDIS_UTIL.SAFEHINCRBY",
		MinArgs: 4,
		MaxArgs: 4,
	}

	if got := item.ToString(); strings.Contains(got, "Mode") {
		t.Errorf("ToString() should omit an empty mode, got %q", got)
	}
}
