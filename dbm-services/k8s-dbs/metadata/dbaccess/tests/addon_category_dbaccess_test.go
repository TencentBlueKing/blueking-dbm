package tests

import (
	"k8s-dbs/metadata/model"
	testutil "k8s-dbs/metadata/util"
	"testing"

	"github.com/stretchr/testify/assert"
)

var sampleCategory = &model.AddonCategoryModel{
	ID:            1,
	CategoryName:  "test-category",
	CategoryAlias: "test-alias",
}

var batchSampleCategories = []*model.AddonCategoryModel{
	{
		ID:            1,
		CategoryName:  "test-category-1",
		CategoryAlias: "test-alias-1",
	},
	{
		ID:            2,
		CategoryName:  "test-category-2",
		CategoryAlias: "test-alias-2",
	},
}

func TestCreateAddonCategory(t *testing.T) {
	dbAccess := testutil.GetAddonCategoryTestDbAccess()
	added, err := dbAccess.Create(sampleCategory)
	assert.NoError(t, err)
	assert.Equal(t, sampleCategory.ID, added.ID)
	assert.Equal(t, sampleCategory.CategoryName, added.CategoryName)
	assert.Equal(t, sampleCategory.CategoryAlias, added.CategoryAlias)
}

func TestGetAddonCategoryByID(t *testing.T) {
	dbAccess := testutil.GetAddonCategoryTestDbAccess()
	_, err := dbAccess.Create(sampleCategory)
	assert.NoError(t, err)

	result, err := dbAccess.FindByID(1)
	assert.NoError(t, err)
	assert.Equal(t, sampleCategory.ID, result.ID)
	assert.Equal(t, sampleCategory.CategoryName, result.CategoryName)
	assert.Equal(t, sampleCategory.CategoryAlias, result.CategoryAlias)
}

func TestListAddonCategories(t *testing.T) {
	dbAccess := testutil.GetAddonCategoryTestDbAccess()
	for _, category := range batchSampleCategories {
		_, err := dbAccess.Create(category)
		assert.NoError(t, err)
	}

	categories, err := dbAccess.ListByLimit(10)
	assert.NoError(t, err)
	assert.Equal(t, len(batchSampleCategories), len(categories))

	categoryMap := make(map[uint64]*model.AddonCategoryModel)
	for _, c := range categories {
		categoryMap[c.ID] = c
	}

	for _, sample := range batchSampleCategories {
		fetchedCategory, ok := categoryMap[sample.ID]
		assert.True(t, ok, "Category with ID %d not found", sample.ID)
		assert.Equal(t, sample.CategoryName, fetchedCategory.CategoryName)
		assert.Equal(t, sample.CategoryAlias, fetchedCategory.CategoryAlias)
	}
}
