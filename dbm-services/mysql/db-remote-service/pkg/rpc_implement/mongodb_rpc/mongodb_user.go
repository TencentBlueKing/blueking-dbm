package mongodb_rpc

import (
	"context"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mymongo"
	"fmt"
	"time"

	"github.com/pkg/errors"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
)

const readAnyDatabase = "readAnyDatabase"

// webconsoleShStatusRole is a minimal custom role for sh.status() on sharded clusters.
const webconsoleShStatusRole = "webconsoleShStatusReader"

// ErrConnectFail is the error when connect to mongodb failed
var ErrConnectFail = fmt.Errorf("connect fail")

type roleRef struct {
	role string
	db   string
}

func roleRefFromBSON(m bson.M) roleRef {
	role, _ := m["role"].(string)
	db, _ := m["db"].(string)
	return roleRef{role: role, db: db}
}

func isMongoVersionAtLeast44(version string) bool {
	major, minor, err := parseMongoVersion(version)
	if err != nil {
		return false
	}
	return major > 4 || (major == 4 && minor >= 4)
}

func needsWebconsoleShStatusRole(clusterType, mongoVersion string) bool {
	return clusterType == ClusterTypeShardedCluster && isMongoVersionAtLeast44(mongoVersion)
}

func expectedWebconsoleRoles(clusterType, mongoVersion string) []roleRef {
	roles := []roleRef{{role: readAnyDatabase, db: "admin"}}
	if needsWebconsoleShStatusRole(clusterType, mongoVersion) {
		roles = append(roles, roleRef{role: webconsoleShStatusRole, db: "admin"})
	}
	return roles
}

func rolesToBSON(roles []roleRef) bson.A {
	out := bson.A{}
	for _, r := range roles {
		out = append(out, bson.D{
			{Key: "role", Value: r.role},
			{Key: "db", Value: r.db},
		})
	}
	return out
}

func existingRolesFromUsersInfo(users bson.A) ([]roleRef, error) {
	if len(users) != 1 {
		if len(users) > 1 {
			return nil, fmt.Errorf("user already exists with multiple roles")
		}
		return nil, nil
	}
	existingUser, ok := users[0].(bson.M)
	if !ok {
		return nil, fmt.Errorf("invalid usersInfo response")
	}
	existingRolesRaw, ok := existingUser["roles"].(bson.A)
	if !ok {
		return nil, fmt.Errorf("invalid usersInfo roles")
	}
	existingRoles := make([]roleRef, 0, len(existingRolesRaw))
	for _, item := range existingRolesRaw {
		roleDoc, ok := item.(bson.M)
		if !ok {
			return nil, fmt.Errorf("invalid usersInfo role entry")
		}
		existingRoles = append(existingRoles, roleRefFromBSON(roleDoc))
	}
	return existingRoles, nil
}

func containsRoleRef(roles []roleRef, target roleRef) bool {
	for _, r := range roles {
		if r.role == target.role && r.db == target.db {
			return true
		}
	}
	return false
}

func missingRoles(existing, expected []roleRef) []roleRef {
	missing := make([]roleRef, 0)
	for _, want := range expected {
		if !containsRoleRef(existing, want) {
			missing = append(missing, want)
		}
	}
	return missing
}

func hasUnexpectedRoles(existing, expected []roleRef) bool {
	for _, got := range existing {
		if !containsRoleRef(expected, got) {
			return true
		}
	}
	return false
}

func connectAdminOnPrimary(host, adminUser, adminPwd string) (*mongo.Client, error) {
	client, err := mymongo.ConnectWithDirect(host, "", adminUser, adminPwd, "admin", 5*time.Second, true)
	if err != nil {
		return nil, errors.Wrap(ErrConnectFail, "connect failed")
	}
	if err = client.Ping(context.Background(), nil); err != nil {
		client.Disconnect(context.TODO())
		return nil, errors.Wrap(ErrConnectFail, "ping failed")
	}
	isMaster, err := mymongo.IsMaster(client, 5)
	if err != nil {
		client.Disconnect(context.TODO())
		return nil, errors.Wrap(ErrConnectFail, "ismaster failed")
	}
	if !isMaster.IsMaster {
		master := isMaster.Primary
		if master == "" {
			client.Disconnect(context.TODO())
			return nil, errors.Wrap(ErrConnectFail, "no primary found")
		}
		client.Disconnect(context.TODO())
		client, err = mymongo.ConnectWithDirect(master, "", adminUser, adminPwd, "admin", 5*time.Second, true)
		if err != nil {
			return nil, fmt.Errorf("failed to connect %s", master)
		}
	}
	return client, nil
}

func ensureShStatusReaderRole(client *mongo.Client) error {
	var result bson.M
	err := client.Database("admin").RunCommand(context.TODO(), bson.D{
		{Key: "rolesInfo", Value: webconsoleShStatusRole},
	}).Decode(&result)
	if err != nil {
		return fmt.Errorf("failed to check role %q: %v", webconsoleShStatusRole, err)
	}
	if roles, ok := result["roles"].(bson.A); ok && len(roles) > 0 {
		return nil
	}

	privileges := bson.A{
		bson.D{
			{Key: "resource", Value: bson.D{{Key: "cluster", Value: true}}},
			{Key: "actions", Value: bson.A{"listShards", "getShardMap", "shardingState"}},
		},
		bson.D{
			{Key: "resource", Value: bson.D{{Key: "db", Value: "config"}, {Key: "collection", Value: ""}}},
			{Key: "actions", Value: bson.A{"find", "listCollections"}},
		},
	}
	err = client.Database("admin").RunCommand(context.TODO(), bson.D{
		{Key: "createRole", Value: webconsoleShStatusRole},
		{Key: "privileges", Value: privileges},
		{Key: "roles", Value: bson.A{}},
	}).Err()
	if err != nil {
		return fmt.Errorf("failed to create role %q: %v", webconsoleShStatusRole, err)
	}
	return nil
}

func grantRoles(client *mongo.Client, user string, roles []roleRef) error {
	if len(roles) == 0 {
		return nil
	}
	err := client.Database("admin").RunCommand(context.TODO(), bson.D{
		{Key: "grantRolesToUser", Value: user},
		{Key: "roles", Value: rolesToBSON(roles)},
	}).Err()
	if err != nil {
		return fmt.Errorf("failed to grant roles to user %q: %v", user, err)
	}
	return nil
}

// createReadOnlyUser creates or upgrades the webconsole read-only user in MongoDB.
func createReadOnlyUser(host, adminUser, adminPwd, tocreateUser, tocreatePwd, clusterType, mongoVersion string) error {
	client, err := connectAdminOnPrimary(host, adminUser, adminPwd)
	if err != nil {
		return err
	}
	defer client.Disconnect(context.TODO())

	expected := expectedWebconsoleRoles(clusterType, mongoVersion)
	if needsWebconsoleShStatusRole(clusterType, mongoVersion) {
		if err = ensureShStatusReaderRole(client); err != nil {
			return err
		}
	}

	var result bson.M
	err = client.Database("admin").RunCommand(context.TODO(), bson.D{
		{Key: "usersInfo", Value: tocreateUser},
	}).Decode(&result)
	if err != nil {
		return fmt.Errorf("failed to check user existence: %v", err)
	}

	if users, ok := result["users"].(bson.A); ok {
		existingRoles, err := existingRolesFromUsersInfo(users)
		if err != nil {
			return err
		}
		if len(existingRoles) > 0 {
			if hasUnexpectedRoles(existingRoles, expected) {
				return fmt.Errorf("user %q already exists with different roles", tocreateUser)
			}
			missing := missingRoles(existingRoles, expected)
			return grantRoles(client, tocreateUser, missing)
		}
	}

	err = client.Database("admin").RunCommand(context.TODO(), bson.D{
		{Key: "createUser", Value: tocreateUser},
		{Key: "pwd", Value: tocreatePwd},
		{Key: "roles", Value: rolesToBSON(expected)},
	}).Err()
	if err != nil {
		return fmt.Errorf("failed to create user, createUser: %s err: %v", tocreateUser, err)
	}
	return nil
}
