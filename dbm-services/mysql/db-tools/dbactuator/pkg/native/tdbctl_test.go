package native_test

import (
	"log"
	"os"
	"strconv"
	"testing"

	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
)

var tdbctldbWork *native.TdbctlDbWork

func init() {
	port, _ := strconv.Atoi(os.Getenv("PORT"))
	conn, err := native.InsObject{
		Host: os.Getenv("HOST"),
		Port: port,
		User: os.Getenv("USER"),
		Pwd:  os.Getenv("PASSWORD"),
	}.Conn()
	if err != nil {
		log.Fatal(err)
	}
	tdbctldbWork = &native.TdbctlDbWork{DbWorker: *conn}
}

func TestTdbctlShowAppProcesslist(t *testing.T) {
	pcls, err := tdbctldbWork.ShowApplicationProcesslist([]string{"root"})
	if err != nil {
		t.Fatal(err)
		return
	}
	t.Log(pcls)
}

func TestTdbctlGetVariables(t *testing.T) {
	val, err := tdbctldbWork.GetSingleGlobalVar("SPT0", "character_set_server")
	if err != nil {
		t.Fatal(err)
		return
	}
	t.Log(val)
}

func TestTdbctlAllVariables(t *testing.T) {
	val, err := tdbctldbWork.QueryGlobalVariables("SPT0")
	if err != nil {
		t.Fatal(err)
		return
	}
	t.Log(val)
}
