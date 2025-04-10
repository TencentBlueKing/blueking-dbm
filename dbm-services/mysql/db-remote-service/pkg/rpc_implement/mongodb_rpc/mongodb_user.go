package mongodb_rpc

import (
	"context"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mymongo"
	"fmt"
	"time"

	"github.com/pkg/errors"

	"go.mongodb.org/mongo-driver/bson"
)

// createReadOnlyUser creates a read-only user in MongoDB
const readAnyDatabase = "readAnyDatabase"

// ErrConnectFail is the error when connect to mongodb failed
var ErrConnectFail = fmt.Errorf("connect fail")

// createReadOnlyUser creates a read-only user in MongoDB
func createReadOnlyUser(host string, adminUser, adminPwd,
	tocreateUser, tocreatePwd string) error {
	readOnlyPriv := bson.A{
		bson.D{
			{Key: "role", Value: readAnyDatabase},
			{Key: "db", Value: "admin"},
		},
	}

	client, err := mymongo.ConnectWithDirect(host, "", adminUser, adminPwd,
		"admin", 5*time.Second, true)
	if err != nil {
		return errors.Wrap(ErrConnectFail, "connect failed")
	}

	err = client.Ping(context.Background(), nil)
	if err != nil {
		return errors.Wrap(ErrConnectFail, "ping failed")
	}

	defer client.Disconnect(context.TODO())

	// detect is Master
	isMaster, err := mymongo.IsMaster(client, 5)
	if err != nil {
		return errors.Wrap(ErrConnectFail, "ismaster failed")
	}

	if isMaster.IsMaster == false {
		master := isMaster.Primary
		if master == "" {
			return errors.Wrap(ErrConnectFail, "no primary found")
		}
		client, err = mymongo.ConnectWithDirect(master, "", adminUser, adminPwd, "admin", 5*time.Second, true)
		if err != nil {
			return fmt.Errorf("failed to connect %s", master)
		}
	}

	// Check if the user already exists
	var result bson.M
	err = client.Database("admin").RunCommand(context.TODO(), bson.D{
		{Key: "usersInfo", Value: tocreateUser},
	}).Decode(&result)
	if err != nil {
		return fmt.Errorf("failed to check user existence: %v", err)
	}

	// Check if the user already exists
	if users, ok := result["users"].(bson.A); ok {
		if len(users) == 1 {
			existingUser := users[0].(bson.M)
			existingRoles := existingUser["roles"].(bson.A)
			// 如果用户已经存在，检查角色只有一个readAnyDatabase权限
			if !(len(existingRoles) == 1 && existingRoles[0].(bson.M)["role"] == readAnyDatabase) {
				return fmt.Errorf("user %q already exists with different roles", tocreateUser)
			}
			return nil
		} else if len(users) > 1 {
			return fmt.Errorf("user %q already exists with multiple roles", tocreateUser)
		}
	}

	// Execute the createUser command
	err = client.Database("admin").RunCommand(context.TODO(), bson.D{
		{Key: "createUser", Value: tocreateUser},
		{Key: "pwd", Value: tocreatePwd},
		{Key: "roles", Value: readOnlyPriv},
	}).Err()
	if err != nil {
		return fmt.Errorf("failed to create user,  createUser: %s err: %v", tocreateUser, err)
	}

	return nil
}
