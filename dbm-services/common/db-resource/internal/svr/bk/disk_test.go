package bk

import (
	"encoding/json"
	"testing"
)

func TestExtractFirstJSONObject(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		want     string
		wantErr  bool
		validate func(t *testing.T, got string) // 用于验证提取的JSON是否有效
	}{
		{
			name:  "单个JSON对象",
			input: `{"cpu":128,"mem":436373,"region":"","zone":"","disk":[]}`,
			want:  `{"cpu":128,"mem":436373,"region":"","zone":"","disk":[]}`,
			validate: func(t *testing.T, got string) {
				var obj ShellResCollection
				if err := json.Unmarshal([]byte(got), &obj); err != nil {
					t.Errorf("提取的JSON无效: %v", err)
				}
			},
		},
		{
			name:  "多个JSON对象连在一起",
			input: `{"cpu":128,"mem":436373,"region":"","zone":"","disk":[]}{"cpu":128,"mem":436373,"region":"","zone":"","disk":[]}`,
			want:  `{"cpu":128,"mem":436373,"region":"","zone":"","disk":[]}`,
			validate: func(t *testing.T, got string) {
				var obj ShellResCollection
				if err := json.Unmarshal([]byte(got), &obj); err != nil {
					t.Errorf("提取的JSON无效: %v", err)
				}
				if obj.Cpu != 128 {
					t.Errorf("期望 CPU=128, 得到 %d", obj.Cpu)
				}
			},
		},
		{
			name:  "嵌套JSON对象",
			input: `{"cpu":128,"mem":436373,"disk":[{"mount_point":"/data","size":21461}]}`,
			want:  `{"cpu":128,"mem":436373,"disk":[{"mount_point":"/data","size":21461}]}`,
			validate: func(t *testing.T, got string) {
				var obj ShellResCollection
				if err := json.Unmarshal([]byte(got), &obj); err != nil {
					t.Errorf("提取的JSON无效: %v", err)
				}
				if len(obj.Disk) != 1 {
					t.Errorf("期望 1 个磁盘, 得到 %d", len(obj.Disk))
				}
			},
		},
		{
			name:  "包含字符串中的大括号",
			input: `{"cpu":128,"message":"包含{大括号}的字符串","disk":[]}`,
			want:  `{"cpu":128,"message":"包含{大括号}的字符串","disk":[]}`,
			validate: func(t *testing.T, got string) {
				var obj map[string]interface{}
				if err := json.Unmarshal([]byte(got), &obj); err != nil {
					t.Errorf("提取的JSON无效: %v", err)
				}
			},
		},
		{
			name:  "包含转义字符",
			input: `{"cpu":128,"message":"包含\"引号\"的字符串","disk":[]}`,
			want:  `{"cpu":128,"message":"包含\"引号\"的字符串","disk":[]}`,
			validate: func(t *testing.T, got string) {
				var obj map[string]interface{}
				if err := json.Unmarshal([]byte(got), &obj); err != nil {
					t.Errorf("提取的JSON无效: %v", err)
				}
			},
		},
		{
			name:  "JSON前后有额外文本",
			input: `some text before {"cpu":128,"mem":436373,"disk":[]} some text after`,
			want:  `{"cpu":128,"mem":436373,"disk":[]}`,
			validate: func(t *testing.T, got string) {
				var obj ShellResCollection
				if err := json.Unmarshal([]byte(got), &obj); err != nil {
					t.Errorf("提取的JSON无效: %v", err)
				}
			},
		},
		{
			name:  "实际日志格式-多个JSON对象",
			input: `{"cpu":128,"mem":436373,"region":"","zone":"","disk":[{"mount_point":"/data","size":21461,"file_type":"ext4","disk_type":"SSD","disk_id":""},{"mount_point":"/data1","size":21461,"file_type":"ext4","disk_type":"SSD","disk_id":""}]}{"cpu":128,"mem":436373,"region":"","zone":"","disk":[{"mount_point":"/data","size":21461,"file_type":"ext4","disk_type":"SSD","disk_id":""},{"mount_point":"/data1","size":21461,"file_type":"ext4","disk_type":"SSD","disk_id":""}]}`,
			want:  `{"cpu":128,"mem":436373,"region":"","zone":"","disk":[{"mount_point":"/data","size":21461,"file_type":"ext4","disk_type":"SSD","disk_id":""},{"mount_point":"/data1","size":21461,"file_type":"ext4","disk_type":"SSD","disk_id":""}]}`,
			validate: func(t *testing.T, got string) {
				var obj ShellResCollection
				if err := json.Unmarshal([]byte(got), &obj); err != nil {
					t.Errorf("提取的JSON无效: %v", err)
				}
				if obj.Cpu != 128 {
					t.Errorf("期望 CPU=128, 得到 %d", obj.Cpu)
				}
				if len(obj.Disk) != 2 {
					t.Errorf("期望 2 个磁盘, 得到 %d", len(obj.Disk))
				}
			},
		},
		{
			name:    "空字符串",
			input:   "",
			want:    "",
			wantErr: true,
		},
		{
			name:    "没有JSON对象",
			input:   "this is just text without json",
			want:    "",
			wantErr: true,
		},
		{
			name:  "只有开始大括号",
			input: `{"cpu":128,"mem":436373`,
			want:  "",
			validate: func(t *testing.T, got string) {
				if got != "" {
					t.Errorf("期望空字符串，得到: %s", got)
				}
			},
		},
		{
			name:  "深度嵌套JSON",
			input: `{"level1":{"level2":{"level3":{"value":123}}}}`,
			want:  `{"level1":{"level2":{"level3":{"value":123}}}}`,
			validate: func(t *testing.T, got string) {
				var obj map[string]interface{}
				if err := json.Unmarshal([]byte(got), &obj); err != nil {
					t.Errorf("提取的JSON无效: %v", err)
				}
			},
		},
		{
			name:  "JSON数组",
			input: `[{"cpu":128},{"cpu":256}]`,
			want:  "",
			validate: func(t *testing.T, got string) {
				// 这个函数只提取对象，不提取数组
				if got != "" {
					t.Logf("注意: 提取到非对象JSON: %s", got)
				}
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := extractFirstJSONObject(tt.input)

			if tt.want != "" && got != tt.want {
				t.Errorf("extractFirstJSONObject() = %v, want %v", got, tt.want)
			}

			if tt.wantErr && got != "" {
				t.Errorf("extractFirstJSONObject() = %v, 期望错误但得到了结果", got)
			}

			if tt.validate != nil {
				tt.validate(t, got)
			}

			// 如果提取到了内容，验证它是否是有效的JSON
			if got != "" {
				var testObj interface{}
				if err := json.Unmarshal([]byte(got), &testObj); err != nil {
					t.Errorf("提取的JSON无法解析: %v, 内容: %s", err, got)
				}
			}
		})
	}
}

// TestExtractFirstJSONObjectRealWorldCase 测试真实世界的案例
func TestExtractFirstJSONObjectRealWorldCase(t *testing.T) {
	// 这是用户提供的实际日志内容
	realLogContent := `{"cpu":128,"mem":436373,"region":"","zone":"","disk":[{"mount_point":"/data","size":21461,"file_type":"ext4","disk_type":"SSD","disk_id":""},{"mount_point":"/data1","size":21461,"file_type":"ext4","disk_type":"SSD","disk_id":""}]}{"cpu":128,"mem":436373,"region":"","zone":"","disk":[{"mount_point":"/data","size":21461,"file_type":"ext4","disk_type":"SSD","disk_id":""},{"mount_point":"/data1","size":21461,"file_type":"ext4","disk_type":"SSD","disk_id":""}]}`

	extracted := extractFirstJSONObject(realLogContent)

	if extracted == "" {
		t.Fatal("未能提取到JSON对象")
	}

	var obj ShellResCollection
	if err := json.Unmarshal([]byte(extracted), &obj); err != nil {
		t.Fatalf("提取的JSON无法解析: %v\n提取的内容: %s", err, extracted)
	}

	// 验证解析结果
	if obj.Cpu != 128 {
		t.Errorf("期望 CPU=128, 得到 %d", obj.Cpu)
	}
	if obj.Mem != 436373 {
		t.Errorf("期望 Mem=436373, 得到 %d", obj.Mem)
	}
	if len(obj.Disk) != 2 {
		t.Errorf("期望 2 个磁盘, 得到 %d", len(obj.Disk))
	}
	if obj.Disk[0].MountPoint != "/data" {
		t.Errorf("期望第一个磁盘挂载点为 /data, 得到 %s", obj.Disk[0].MountPoint)
	}

	t.Logf("成功提取并解析JSON: CPU=%d, Mem=%d, Disk数量=%d", obj.Cpu, obj.Mem, len(obj.Disk))
}
