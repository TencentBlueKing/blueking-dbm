package provider

import (
	"k8s-dbs/src/metadata/dbaccess"
	models "k8s-dbs/src/metadata/dbaccess/model"
	entitys "k8s-dbs/src/metadata/provider/entity"
	"log/slog"

	"github.com/jinzhu/copier"
)

type K8sCrdClusterDefinitionProvider interface {
	CreateClusterDefinition(entity *entitys.K8sCrdClusterDefinitionEntity) (*entitys.K8sCrdClusterDefinitionEntity, error)
	DeleteClusterDefinitionById(id uint64) (uint64, error)
	FindClusterDefinitionById(id uint64) (*entitys.K8sCrdClusterDefinitionEntity, error)
	UpdateClusterDefinition(entity *entitys.K8sCrdClusterDefinitionEntity) (uint64, error)
}

type K8sCrdClusterDefinitionProviderImpl struct {
	dbAccess dbaccess.K8sCrdClusterDefinitionDbAccess
}

func (k *K8sCrdClusterDefinitionProviderImpl) CreateClusterDefinition(entity *entitys.K8sCrdClusterDefinitionEntity) (*entitys.K8sCrdClusterDefinitionEntity, error) {
	cdModel := models.K8sCrdClusterDefinitionModel{}
	err := copier.Copy(&cdModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model")
		return nil, err
	}
	addedCdModel, err := k.dbAccess.Create(&cdModel)
	if err != nil {
		slog.Error("Failed to create model")
		return nil, err
	} else {
		cdEntity := entitys.K8sCrdClusterDefinitionEntity{}
		err := copier.Copy(&cdEntity, addedCdModel)
		if err != nil {
			slog.Error("Failed to copy entity to copied model")
			return nil, err
		} else {
			return &cdEntity, nil
		}
	}
}

func (k *K8sCrdClusterDefinitionProviderImpl) DeleteClusterDefinitionById(id uint64) (uint64, error) {
	return k.dbAccess.DeleteById(id)
}

func (k *K8sCrdClusterDefinitionProviderImpl) FindClusterDefinitionById(id uint64) (*entitys.K8sCrdClusterDefinitionEntity, error) {
	cdModel, err := k.dbAccess.FindById(id)
	if err != nil {
		slog.Error("Failed to find entity", "error", err)
		return nil, err
	} else {
		cdEntity := entitys.K8sCrdClusterDefinitionEntity{}
		err := copier.Copy(&cdEntity, cdModel)
		if err != nil {
			slog.Error("Failed to copy entity to copied model", "error", err)
			return nil, err
		} else {
			return &cdEntity, nil
		}
	}
}

func (k *K8sCrdClusterDefinitionProviderImpl) UpdateClusterDefinition(entity *entitys.K8sCrdClusterDefinitionEntity) (uint64, error) {
	cdModel := models.K8sCrdClusterDefinitionModel{}
	err := copier.Copy(&cdModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return 0, err
	}
	rows, err := k.dbAccess.Update(&cdModel)
	if err != nil {
		slog.Error("Failed to update entity", "error", err)
		return 0, err
	} else {
		return rows, nil
	}
}

func NewK8sCrdClusterDefinitionProvider(dbAccess dbaccess.K8sCrdClusterDefinitionDbAccess) K8sCrdClusterDefinitionProvider {
	return &K8sCrdClusterDefinitionProviderImpl{dbAccess}
}
