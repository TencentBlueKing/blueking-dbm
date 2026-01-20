package main

import (
	"fmt"
	"os"

	"dbm-services/common/go-pubpkg/cc.v3"
)

// Example 1: 不使用租户 ID（向后兼容）
func exampleWithoutTenant() {
	client, err := cc.NewClient("http://bk-cmdb", cc.Secret{
		BKAppCode:   "bk-dbm",
		BKAppSecret: "your_secret",
		BKUsername:  "admin",
	})
	if err != nil {
		fmt.Printf("创建客户端失败: %v\n", err)
		return
	}

	// 使用 client 发送请求
	// 不会添加 X-Bk-Tenant-Id header
	resp, err := client.Do("POST", "/api/v3/findmany/hosts", map[string]interface{}{
		"bk_biz_id": 2,
	})
	if err != nil {
		fmt.Printf("请求失败: %v\n", err)
		return
	}

	fmt.Printf("响应: %+v\n", resp)
}

// Example 2: 使用固定租户 ID
func exampleWithFixedTenant() {
	client, err := cc.NewClientWithTenant("http://bk-cmdb", cc.Secret{
		BKAppCode:   "bk-dbm",
		BKAppSecret: "your_secret",
		BKUsername:  "admin",
	}, "system") // 固定使用 system 租户
	if err != nil {
		fmt.Printf("创建客户端失败: %v\n", err)
		return
	}

	// 使用 client 发送请求
	// 会自动添加 X-Bk-Tenant-Id: system header
	resp, err := client.Do("POST", "/api/v3/findmany/hosts", map[string]interface{}{
		"bk_biz_id": 2,
	})
	if err != nil {
		fmt.Printf("请求失败: %v\n", err)
		return
	}

	fmt.Printf("响应: %+v\n", resp)
}

// Example 3: 从环境变量读取租户 ID
func exampleWithEnvTenant() {
	// 从环境变量读取租户 ID，如果没有设置则为空字符串（不添加 header）
	tenantID := os.Getenv("BK_TENANT_ID")

	client, err := cc.NewClientWithTenant("http://bk-cmdb", cc.Secret{
		BKAppCode:   "bk-dbm",
		BKAppSecret: "your_secret",
		BKUsername:  "admin",
	}, tenantID)
	if err != nil {
		fmt.Printf("创建客户端失败: %v\n", err)
		return
	}

	// 使用 client 发送请求
	// 如果 BK_TENANT_ID 环境变量有值，会添加 X-Bk-Tenant-Id header
	resp, err := client.Do("POST", "/api/v3/findmany/hosts", map[string]interface{}{
		"bk_biz_id": 2,
	})
	if err != nil {
		fmt.Printf("请求失败: %v\n", err)
		return
	}

	fmt.Printf("响应: %+v\n", resp)
}

// Example 4: 从配置文件读取（伪代码）
func exampleWithConfigTenant() {
	// 假设有一个配置结构
	type Config struct {
		EnableMultiTenantMode bool
		TenantID              string
	}

	// 从配置文件读取（这里用硬编码示例）
	config := Config{
		EnableMultiTenantMode: true,
		TenantID:              "system",
	}

	// 根据配置决定是否使用租户 ID
	var tenantID string
	if config.EnableMultiTenantMode {
		tenantID = config.TenantID
	}

	client, err := cc.NewClientWithTenant("http://bk-cmdb", cc.Secret{
		BKAppCode:   "bk-dbm",
		BKAppSecret: "your_secret",
		BKUsername:  "admin",
	}, tenantID)
	if err != nil {
		fmt.Printf("创建客户端失败: %v\n", err)
		return
	}

	// 使用 client 发送请求
	resp, err := client.Do("POST", "/api/v3/findmany/hosts", map[string]interface{}{
		"bk_biz_id": 2,
	})
	if err != nil {
		fmt.Printf("请求失败: %v\n", err)
		return
	}

	fmt.Printf("响应: %+v\n", resp)
}

func main() {
	fmt.Println("=== Example 1: 不使用租户 ID ===")
	// exampleWithoutTenant()

	fmt.Println("\n=== Example 2: 使用固定租户 ID ===")
	// exampleWithFixedTenant()

	fmt.Println("\n=== Example 3: 从环境变量读取租户 ID ===")
	// exampleWithEnvTenant()

	fmt.Println("\n=== Example 4: 从配置文件读取租户 ID ===")
	// exampleWithConfigTenant()

	fmt.Println("\n所有示例代码已准备好，取消注释即可运行")
}
