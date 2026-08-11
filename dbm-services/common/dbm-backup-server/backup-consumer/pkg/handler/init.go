package handler

import (
	"gorm.io/gorm"
)

type RegisterHandler struct {
	Ready chan bool
	Db    *gorm.DB
}
