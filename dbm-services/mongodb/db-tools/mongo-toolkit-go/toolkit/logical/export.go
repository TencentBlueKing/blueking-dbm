package logical

import (
	"dbm-services/common/go-pubpkg/mycmd"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mymongo"
	"fmt"
	"path"
	"time"

	"github.com/pkg/errors"
	log "github.com/sirupsen/logrus"
)

const (
	LOG_FILE_NAME = "export.log"
)

// ExportArgs export parameters
type ExportArgs struct {
	Query  string `json:"query"`  // Query filter for documents
	Fields string `json:"fields"` // Specific fields to export
	Format string `json:"format"` // Export format: json, csv
	Limit  int    `json:"limit"`  // Limit number of documents
	Skip   int    `json:"skip"`   // Skip number of documents
	Sort   string `json:"sort"`   // Sort specification
}

// MongoExportHelper handles mongoexport operations
type MongoExportHelper struct {
	MongoHost      *mymongo.MongoHost
	MongoExportBin string
	User           string
	Pass           string
	AuthDb         string
	OsUser         string // OS user to run commands as
}

// NewMongoExportHelper creates a new MongoExportHelper instance
func NewMongoExportHelper(host *mymongo.MongoHost, exportBin, user, pass, authDb string, osUser string) *MongoExportHelper {
	return &MongoExportHelper{
		MongoHost:      host,
		MongoExportBin: exportBin,
		User:           user,
		Pass:           pass,
		AuthDb:         authDb,
		OsUser:         osUser,
	}
}

// ExportCollection exports a single collection to a file
func (m *MongoExportHelper) ExportCollection(database, collection, outputDir string, args *ExportArgs) (cmdLine string, err error) {
	if database == "" || collection == "" {
		return "", errors.New("database and collection are required")
	}

	// Set default format if not specified
	format := "json"
	if args != nil && args.Format != "" {
		format = args.Format
	}

	// Validate format
	if format != "json" && format != "csv" {
		return "", errors.New("format must be 'json' or 'csv'")
	}

	// Build output file path
	outputPath := path.Join(outputDir, fmt.Sprintf("%s.%s.%s", database, collection, format))
	logFilePath := path.Join(outputDir, LOG_FILE_NAME)

	// Build mongoexport command
	exportCmd := mycmd.New(m.MongoExportBin,
		"-u", m.User,
		"-p", mycmd.Password(m.Pass),
		"--host", mycmd.Val(m.MongoHost.Host),
		"--port", m.MongoHost.Port,
		"--authenticationDatabase="+m.AuthDb,
		"-d", database,
		"-c", collection,
		"--type", format,
	)

	// Add optional parameters
	if args != nil {
		if args.Query != "" {
			exportCmd.Append("--query", mycmd.Val(args.Query))
		}
		if args.Fields != "" {
			exportCmd.Append("--fields", mycmd.Val(args.Fields))
		}
		if args.Limit > 0 {
			exportCmd.Append("--limit", fmt.Sprintf("%d", args.Limit))
		}
		if args.Skip > 0 {
			exportCmd.Append("--skip", fmt.Sprintf("%d", args.Skip))
		}
		if args.Sort != "" {
			exportCmd.Append("--sort", mycmd.Val(args.Sort))
		}
	}

	exportCmd.Append(
		"-o", outputPath, ">>", logFilePath, "2>&1",
	)

	_, _, _, err = exportCmd.RunByBash(m.OsUser, time.Hour*24)
	return exportCmd.GetCmdLine(m.OsUser, true), errors.Wrap(err, "ExportCollection")
}

// ExportWithFilter exports collections based on namespace filter
func (m *MongoExportHelper) ExportWithFilter(outputDir string, filter *NsFilter, args *ExportArgs) (cmdLines []string, cmdLine string, err error) {
	if filter == nil {
		return nil, "", errors.New("filter is required")
	}

	// Get database and collection list with filter
	dbColList, err := GetDbCollectionWithFilter(m.MongoHost.Host, m.MongoHost.Port, m.User, m.Pass, m.AuthDb, filter, true)
	if err != nil {
		return nil, "", errors.Wrap(err, "GetDbCollectionWithFilter")
	}

	for _, dbRow := range dbColList {
		// Skip if no matching collections
		if len(dbRow.Col) == 0 {
			continue
		}

		// Export each collection in the database
		for _, collection := range dbRow.Col {
			cmdLine, err := m.ExportCollection(dbRow.Db, collection, outputDir, args)
			if err != nil {
				log.Errorf("Failed to export collection %s.%s: %v", dbRow.Db, collection, err)
				return cmdLines, cmdLine, errors.Wrapf(err, "export collection %s.%s", dbRow.Db, collection)
			}
			cmdLines = append(cmdLines, cmdLine)
			log.Infof("Successfully exported collection %s.%s", dbRow.Db, collection)
		}
	}

	return cmdLines, cmdLine, nil
}
