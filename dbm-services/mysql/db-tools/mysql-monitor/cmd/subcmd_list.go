package cmd

// var subCmdList = &cobra.Command{
//	Use:   "list",
//	Short: "list registered monitor items",
//	Long:  "list registered monitor items",
//	RunE: func(cmd *cobra.Command, args []string) error {
//		err := config.InitConfig()
//		if err != nil {
//			return err
//		}
//		initLogger(config.MonitorConfig.Log)
//
//		for k, _ := range items_collect.RegisteredItemConstructor() {
//			fmt.Println(k)
//		}
//		return nil
//	},
// }
//
// func init() {
//	rootCmd.AddCommand(subCmdList)
// }
