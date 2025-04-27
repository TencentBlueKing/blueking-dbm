package provider

import (
	"k8s-dbs/src/metadata/dbaccess"
	models "k8s-dbs/src/metadata/dbaccess/model"
	entitys "k8s-dbs/src/metadata/provider/entity"
	"log/slog"

	"github.com/jinzhu/copier"
)

type K8sCrdComponentDefinitionProvider interface {
	CreateComponentDefinition(entity *entitys.K8sCrdComponentDefinitionEntity) (*entitys.K8sCrdComponentDefinitionEntity, error)
	DeleteComponentDefinitionById(id uint64) (uint64, error)
	FindComponentDefinitionById(id uint64) (*entitys.K8sCrdComponentDefinitionEntity, error)
	UpdateComponentDefinition(entity *entitys.K8sCrdComponentDefinitionEntity) (uint64, error)
}

type K8sCrdComponentDefinitionProviderImpl struct {
	dbAccess dbaccess.K8sCrdComponentDefinitionDbAccess
}

func (k *K8sCrdComponentDefinitionProviderImpl) CreateComponentDefinition(componentDefinition *entitys.K8sCrdComponentDefinitionEntity) (*entitys.K8sCrdComponentDefinitionEntity, error) {
	K8sCrdComponentDefinitionModel := models.K8sCrdComponentDefinitionModel{}
	err := copier.Copy(&K8sCrdComponentDefinitionModel, componentDefinition)
	if err != nil {
		slog.Error("Failed to copy model to copied model", "error", err)
		return nil, err
	}
	addedCmpdModel, err := k.dbAccess.Create(&K8sCrdComponentDefinitionModel)
	if err != nil {
		slog.Error("Failed to create model", "error", err)
		return nil, err
	} else {
		componentDefinitionEntity := entitys.K8sCrdComponentDefinitionEntity{}
		err := copier.Copy(&componentDefinitionEntity, addedCmpdModel)
		if err != nil {
			slog.Error("Failed to copy model to copied model", "error", err)
			return nil, err
		} else {
			return &componentDefinitionEntity, nil
		}
	}
}

func (k *K8sCrdComponentDefinitionProviderImpl) DeleteComponentDefinitionById(id uint64) (uint64, error) {
	return k.dbAccess.DeleteById(id)
}

func (k *K8sCrdComponentDefinitionProviderImpl) FindComponentDefinitionById(id uint64) (*entitys.K8sCrdComponentDefinitionEntity, error) {
	componentDefinitionModel, err := k.dbAccess.FindById(id)
	if err != nil {
		slog.Error("Failed to delete model", "error", err)
		return nil, err
	} else {
		componentDefinitionEntity := entitys.K8sCrdComponentDefinitionEntity{}
		err := copier.Copy(&componentDefinitionEntity, componentDefinitionModel)
		if err != nil {
			slog.Error("Failed to copy model to copied model", "error", err)
			return nil, err
		} else {
			return &componentDefinitionEntity, nil
		}
	}
}

func (k *K8sCrdComponentDefinitionProviderImpl) UpdateComponentDefinition(componentDefinition *entitys.K8sCrdComponentDefinitionEntity) (uint64, error) {
	componentDefinitionModel := models.K8sCrdComponentDefinitionModel{}
	err := copier.Copy(&componentDefinitionModel, componentDefinition)
	if err != nil {
		slog.Error("Failed to copy model to copied model", "error", err)
		return 0, err
	}
	rows, err := k.dbAccess.Update(&componentDefinitionModel)
	if err != nil {
		slog.Error("Failed to update model", "error", err)
		return 0, err
	} else {
		return rows, nil
	}
}

func NewK8sCrdComponentDefinitionProvider(dbAccess dbaccess.K8sCrdComponentDefinitionDbAccess) K8sCrdComponentDefinitionProvider {
	return &K8sCrdComponentDefinitionProviderImpl{dbAccess}
}
