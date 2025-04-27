package dbaccess

import (
	models "k8s-dbs/src/metadata/dbaccess/model"
	"k8s-dbs/src/metadata/utils"
	"log/slog"

	"gorm.io/gorm"
)

type ClusterRequestRecordDbAccess interface {
	Create(model *models.ClusterRequestRecordModel) (*models.ClusterRequestRecordModel, error)
	DeleteById(id uint64) (uint64, error)
	FindById(id uint64) (*models.ClusterRequestRecordModel, error)
	Update(model *models.ClusterRequestRecordModel) (uint64, error)
	ListByPage(pagination utils.Pagination) ([]models.ClusterRequestRecordModel, int64, error)
}

type ClusterRequestRecordDbAccessImpl struct {
	db *gorm.DB
}

func (k *ClusterRequestRecordDbAccessImpl) Create(model *models.ClusterRequestRecordModel) (*models.ClusterRequestRecordModel, error) {
	if err := k.db.Create(model).Error; err != nil {
		slog.Error("Create request error", "error", err)
		return nil, err
	}
	var addedRequest models.ClusterRequestRecordModel
	if err := k.db.First(&addedRequest, "id=?", model.ID).Error; err != nil {
		slog.Error("Find request error", "error", err)
		return nil, err
	} else {
		return &addedRequest, nil
	}
}

func (k *ClusterRequestRecordDbAccessImpl) DeleteById(id uint64) (uint64, error) {
	result := k.db.Delete(&models.ClusterRequestRecordModel{}, id)
	if result.Error != nil {
		slog.Error("Delete request error", "error", result.Error.Error())
		return 0, result.Error
	} else {
		return uint64(result.RowsAffected), nil
	}
}

func (k *ClusterRequestRecordDbAccessImpl) FindById(id uint64) (*models.ClusterRequestRecordModel, error) {
	var request models.ClusterRequestRecordModel
	result := k.db.First(&request, id)
	if result.Error != nil {
		slog.Error("Find request error", "error", result.Error.Error())
		return nil, result.Error
	} else {
		return &request, nil
	}
}

func (k *ClusterRequestRecordDbAccessImpl) Update(model *models.ClusterRequestRecordModel) (uint64, error) {
	result := k.db.Omit("CreatedAt", "CreatedBy").Save(model)
	if result.Error != nil {
		slog.Error("Update request error", "error", result.Error.Error())
		return 0, result.Error
	} else {
		return uint64(result.RowsAffected), nil
	}
}

func (k *ClusterRequestRecordDbAccessImpl) ListByPage(pagination utils.Pagination) ([]models.ClusterRequestRecordModel, int64, error) {
	//TODO implement me
	panic("implement me")
}

func NewClusterRequestRecordDbAccess(db *gorm.DB) ClusterRequestRecordDbAccess {
	return &ClusterRequestRecordDbAccessImpl{db: db}
}
