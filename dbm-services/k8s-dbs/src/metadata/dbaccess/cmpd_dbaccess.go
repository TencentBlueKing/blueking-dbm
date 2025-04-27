package dbaccess

import (
	models "k8s-dbs/src/metadata/dbaccess/model"
	"k8s-dbs/src/metadata/utils"
	"log/slog"

	"gorm.io/gorm"
)

type K8sCrdComponentDefinitionDbAccess interface {
	Create(model *models.K8sCrdComponentDefinitionModel) (*models.K8sCrdComponentDefinitionModel, error)
	DeleteById(id uint64) (uint64, error)
	FindById(id uint64) (*models.K8sCrdComponentDefinitionModel, error)
	Update(model *models.K8sCrdComponentDefinitionModel) (uint64, error)
	ListByPage(pagination utils.Pagination) ([]models.K8sCrdComponentDefinitionModel, int64, error)
}

type K8sCrdComponentDefinitionDbAccessImpl struct {
	db *gorm.DB
}

func (this *K8sCrdComponentDefinitionDbAccessImpl) Create(componentDefinition *models.K8sCrdComponentDefinitionModel) (*models.K8sCrdComponentDefinitionModel, error) {
	if err := this.db.Create(componentDefinition).Error; err != nil {
		slog.Error("Create componentdefinition error", "error", err)
		return nil, err
	}
	var addedComponentDefinition models.K8sCrdComponentDefinitionModel
	if err := this.db.First(&addedComponentDefinition, "componentdefinition_name=?", componentDefinition.ComponentDefinitionName).Error; err != nil {
		slog.Error("Find componentdefinition error", "error", err)
		return nil, err
	} else {
		return &addedComponentDefinition, nil
	}
}

func (this *K8sCrdComponentDefinitionDbAccessImpl) DeleteById(id uint64) (uint64, error) {
	result := this.db.Delete(&models.K8sCrdComponentDefinitionModel{}, id)
	if result.Error != nil {
		slog.Error("Delete componentdefinition error", "error", result.Error.Error())
		return 0, result.Error
	} else {
		return uint64(result.RowsAffected), nil
	}
}

func (this *K8sCrdComponentDefinitionDbAccessImpl) FindById(id uint64) (*models.K8sCrdComponentDefinitionModel, error) {
	var componentDefinition models.K8sCrdComponentDefinitionModel
	result := this.db.First(&componentDefinition, id)
	if result.Error != nil {
		slog.Error("Find componentdefinition error", "error", result.Error.Error())
		return nil, result.Error
	} else {
		return &componentDefinition, nil
	}
}

func (this *K8sCrdComponentDefinitionDbAccessImpl) Update(componentDefinition *models.K8sCrdComponentDefinitionModel) (uint64, error) {
	result := this.db.Omit("CreatedAt", "CreatedBy").Save(componentDefinition)
	if result.Error != nil {
		slog.Error("Update componentdefinition error", "error", result.Error.Error())
		return 0, result.Error
	} else {
		return uint64(result.RowsAffected), nil
	}
}

func (this *K8sCrdComponentDefinitionDbAccessImpl) ListByPage(pagination utils.Pagination) ([]models.K8sCrdComponentDefinitionModel, int64, error) {
	//TODO implement me
	panic("implement me")
}

func NewK8sCrdComponentDefinitionDbAccess(db *gorm.DB) K8sCrdComponentDefinitionDbAccess {
	return &K8sCrdComponentDefinitionDbAccessImpl{db: db}
}
