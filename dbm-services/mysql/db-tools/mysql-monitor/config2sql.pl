use strict;
use warnings;
use YAML::XS qw(LoadFile);
use JSON qw(encode_json);

my $items_config = LoadFile('items-config.yaml');

sub generate_sql {
    my $dbtype = shift;
    print "DELETE FROM tb_config_name_def WHERE namespace = '$dbtype' AND  conf_type = 'mysql_monitor' AND conf_file = 'items-config.yaml';" . "\n";
    foreach my $item (@$items_config) {
        my $item_value = encode_json($item);
        $item_value =~ s/"enable":"1"/"enable":true/;
        $item_value =~ s/"enable":"0"/"enable":false/;
        $item_value =~ s/"enable":""/"enable":false/;
        $item_value =~ s/"topk_num":"0"/"topk_num":0/;
        $item_value =~ s/"disable_merge_partition":""/"disable_merge_partition":false/;
        $item_value =~ s/"disable_merge_rules":""/"disable_merge_rules":false/;

        my $sql = sprintf(q#REPLACE INTO
        tb_config_name_def(
            namespace, conf_type, conf_file, conf_name,
            value_type, value_default, value_allowed, value_type_sub,
            flag_status, flag_disable, flag_locked, flag_encrypt, need_restart)
            VALUES(
                '%s', 'mysql_monitor', 'items-config.yaml', '%s',
                 'STRING', '%s', '', 'MAP',
                 1, 0, 0, 0, 1);#,
            $dbtype, $item->{name}, $item_value);
        # 没什么实际的意义, 只是让输入的 sql 好看些
        $sql =~ s/\n//g;
        $sql =~ s/\s+/ /g;
        print $sql . "\n";
    }
    print "\n";
}

generate_sql('tendb');
generate_sql('tendbha');
generate_sql('tendbsingle');
generate_sql('tendbcluster');