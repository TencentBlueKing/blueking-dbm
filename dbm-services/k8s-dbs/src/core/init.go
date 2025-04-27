package core

import (
	"k8s-dbs/src/core/client"
	"log"
	"log/slog"
)

func Init() error {
	if err := InitDB(); err != nil {
		return err
	}
	return nil
}

func InitDB() error {
	log.Println("Start to initial MySql Connection...")
	if err := client.Db.Init(); err != nil {
		slog.Error("Failed to initial MySql Connection", "error", err)
		return err
	}
	log.Println("Finish initialize MySql Connection...")
	return nil
}
