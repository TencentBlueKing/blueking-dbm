package dbaccess

import (
	models "k8s-dbs/src/metadata/dbaccess/model"
	"k8s-dbs/src/metadata/utils"
	"log/slog"

	"gorm.io/gorm"
)

type K8sCrdComponentDbAccess interface {
	Create(model *models.K8sCrdComponentModel) (*models.K8sCrdComponentModel, error)
	DeleteById(id uint64) (uint64, error)
	FindById(id uint64) (*models.K8sCrdComponentModel, error)
	Update(model *models.K8sCrdComponentModel) (uint64, error)
	ListByPage(pagination utils.Pagination) ([]models.K8sCrdComponentModel, int64, error)
}

type K8sCrdComponentDbAccessImpl struct {
	db *gorm.DB
}

func (this *K8sCrdComponentDbAccessImpl) Create(model *models.K8sCrdComponentModel) (*models.K8sCrdComponentModel, error) {
	if err := this.db.Create(model).Error; err != nil {
		slog.Error("Create model error", "error", err)
		return nil, err
	}
	var addedComponent models.K8sCrdComponentModel
	if err := this.db.First(&addedComponent, "id=?", model.ID).Error; err != nil {
		slog.Error("Find component error", "error", err)
		return nil, err
	} else {
		return &addedComponent, nil
	}
}

func (this *K8sCrdComponentDbAccessImpl) DeleteById(id uint64) (uint64, error) {
	result := this.db.Delete(&models.K8sCrdComponentModel{}, id)
	if result.Error != nil {
		slog.Error("Delete component error", "error", result.Error.Error())
		return 0, result.Error
	} else {
		return uint64(result.RowsAffected), nil
	}
}

func (this *K8sCrdComponentDbAccessImpl) FindById(id uint64) (*models.K8sCrdComponentModel, error) {
	var component models.K8sCrdComponentModel
	result := this.db.First(&component, id)
	if result.Error != nil {
		slog.Error("Find component error", "error", result.Error.Error())
		return nil, result.Error
	} else {
		return &component, nil
	}
}

func (this *K8sCrdComponentDbAccessImpl) Update(model *models.K8sCrdComponentModel) (uint64, error) {
	result := this.db.Omit("CreatedAt", "CreatedBy").Save(model)
	if result.Error != nil {
		slog.Error("Update component error", "error", result.Error.Error())
		return 0, result.Error
	} else {
		return uint64(result.RowsAffected), nil
	}
}

func (this *K8sCrdComponentDbAccessImpl) ListByPage(pagination utils.Pagination) ([]models.K8sCrdComponentModel, int64, error) {
	//TODO implement me
	panic("implement me")
}

func NewK8sCrdComponentAccess(db *gorm.DB) K8sCrdComponentDbAccess {
	return &K8sCrdComponentDbAccessImpl{db: db}
}
