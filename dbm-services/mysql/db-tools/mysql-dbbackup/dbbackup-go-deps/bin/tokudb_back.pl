#!/usr/bin/perl

use FindBin qw($Bin);

use warnings;
use strict;
use Getopt::Long qw(:config posix_default);
use POSIX qw(strftime);
use File::Copy qw(copy);
use Data::Dumper;
use DBI;
use File::Find;
no warnings 'File::Find';

my $user='';
my $password='';
my $sock='';
my $host='localhost';
my $port=3306;
my $increment=0;
my $lock_wait_timeout = undef;
my $dump_slave = undef;
my $global_time_offset=0;
my @tokudb_backup_warnings;
sub tmysql_version_parser {
    my $mysql_version = shift;
    if($mysql_version =~ /tmysql/){
        return sprintf( '%03d%03d%03d', $mysql_version =~ m/tmysql-([012345678])\.(\d+)\.*(\d*)/g );
    }else{
        return '000000000';
    }
}

Getopt::Long::Configure ("bundling_override");
GetOptions(
	'host|h=s'      => \$host,
        'password|p=s'  => \$password,
        'port|P=s'      => \$port,
        'user|u=s'      => \$user,
	'socket|S=s'    => \$sock,
    'increment|i!'  => \$increment,
	'flush-wait-timeout=s' => \$lock_wait_timeout,
        'dump-slave!'   => \$dump_slave
)or die "usage: xxx -u user -p password -h host -P port [-i|increment] backdir/target_name(when enable increment,there shoud be previous file in backdir) global_time_offset";


my $backdir= $ARGV[0];

if( -d $backdir){
}else{
    mkdir("$backdir") or die "mkdir $backdir fail";
}
if(defined $ARGV[1] and $ARGV[1]=~ /\s*(\d+)\s*/){
    $global_time_offset=$1;
}
mkdir("$backdir/mysql_data");
mkdir("$backdir/tokudb_data");
mkdir("$backdir/tokudb_log");
mkdir("$backdir/innodb_data");

if ($sock =~ /.+\/(\d+)\// ) {
    $port = $1;
}

my $data_dir        = undef;
my $tokudb_data_dir = undef;
my $tokudb_log_dir  = undef;
my $innodb_home_dir      = undef;
my $innodb_log_dir      = undef;
my $myconf = ($port == 3306)? "/etc/my.cnf" : "/etc/my.cnf.$port";

open( my $my_cnf_fp, "< $myconf" ) or die "$myconf open error" ;
while ( my $line = <$my_cnf_fp> ) {
    chomp $line;
    if ( not defined $data_dir ) {
        if ( $line =~ /\s*datadir\s*=\s*([\S]+)/ ) {
            $data_dir = $1;
            next;
        }
    }
    if ( not defined $tokudb_data_dir ) {
        if ( $line =~ /\s*tokudb_data_dir\s*=\s*([\S]+)/ ) {
            $tokudb_data_dir = $1;
            next;
        }
    }
    if ( not defined $tokudb_log_dir ) {
        if ( $line =~ /\s*tokudb_log_dir\s*=\s*([\S]+)/ ) {
        $tokudb_log_dir = $1;
        next;
        }
    }
    if ( not defined $innodb_home_dir ) {
        if ( $line =~ /\s*innodb_data_home_dir\s*=\s*([\S]+)/ ) {
        $innodb_home_dir = $1;
        next;
        }
    }
    if ( not defined $innodb_log_dir ) {
        if ( $line =~ /\s*innodb_log_group_home_dir\s*=\s*([\S]+)/ ) {
        $innodb_log_dir = $1;
        next;
        }
    }
}
close($my_cnf_fp);

unless (defined $data_dir &&
        defined $tokudb_data_dir &&
        defined $tokudb_log_dir &&
        defined $innodb_home_dir )
{
    die "some key in $myconf lost";
}

my $fully_stamp=(time)+$global_time_offset;
#system("date '+%s' > $backdir/TOKUDB.BEGIN");
my $date=strftime("%Y%m%d_%H%M%S", localtime($fully_stamp));

my $backed_debug_log_file="$backdir/debug_log.txt";
my $debug_log_file="$Bin/debug_log_tokudb.txt";
open my $backed_debug_log,">$backed_debug_log_file" or die "failed to open $backed_debug_log_file for:$!\n";
open my $debug_log,">>$debug_log_file" or die "failed to open $debug_log_file for:$!\n";
print $debug_log "\nport:$port time:$date\n";
print $backed_debug_log "\nport:$port time:$date\n";

system("echo $date >> $backdir/TOKUDB.BEGIN");
my $tname=( split(/\//,$ARGV[0]) )[-1];
my $dir;
if($ARGV[0] =~ /(.+)\/${tname}$/){
    $dir=$1;   
}else{
    die "failed while parsing backdir";
}
my $fully_name=$tname;
my $dbh = DBI->connect ("DBI:mysql:mysql:host=$host:port=$port:mysql_socket=$sock", $user, $password);

my $sql = qq{ select version() };
my $row_ref     = $dbh->selectrow_arrayref($sql);
my $tmysql_ver = tmysql_version_parser($row_ref->[0]);

if($tmysql_ver lt tmysql_version_parser("tmysql-2.1.3")){
    die "tokudb physical backup only avaliable above tmysql-2.1.3";
}

if(defined $lock_wait_timeout and $lock_wait_timeout ne '0'){
    $dbh->do("SET LOCK_WAIT_TIMEOUT=$lock_wait_timeout;") or die "Set lock_wait_timeout failed!";
}

##### STEP 1. set tokudb_commit_sync=1:close redo log buffer
#my $ret=$dbh->do("start transaction");
#die "unable to start transaction for close redo log buffer" if not defined $ret or $ret<0;
#$sql = qq{ select \@\@tokudb_commit_sync };
#$row_ref = $dbh->selectrow_arrayref($sql);
#my $old_global_tokudb_commit_sync=$row_ref->[0];
#$ret=$dbh->do("set global tokudb_commit_sync=1");
#die "unable to set global tokudb_commit_sync=1" if not defined $ret or $ret<0;
#$ret=$dbh->do("commit");
#die "unable commit set global tokudb_commit_sync=1" if not defined $ret or $ret<0;
#print qx(date);
#print "unable redo log buffer ok\n\n";


##### STEP 2. get METADATA lock for each table
if($tmysql_ver ge tmysql_version_parser("tmysql-2.1.3")){
    $dbh->do("lock tables for backup;") or die "Get metadata lock failed";
    print $debug_log qx(date);
    print $debug_log "get metadata lock ok\n\n";
}

my @white_databases=qw(information_schema db_infobase mysql performance_schema test sys infodba_schema);
my @backup_databases;
my @other_engines;
eval{
    local $SIG{__DIE__} = "";           
    $sql="show databases";
    my $select=$dbh->prepare($sql);
    $select->execute();
    while(my $result=($select->fetchrow_array)[0]){
        if(not grep(/$result/,@white_databases)){
            push(@backup_databases,$result);   
        }
    }
    if(@backup_databases){
        my $database_string=join("','",@backup_databases);
        $sql="select distinct engine from information_schema.tables where table_schema in('$database_string')";
        $select=$dbh->prepare($sql);
        $select->execute();
        while(my @row_array=$select->fetchrow_array){
            my ($engine)=@row_array;
            if(not $engine eq 'TokuDB'){
                push(@other_engines,$engine);   
            }
        }
    }
};
if($@){
    die "check engine for all backup table failed:$@\n";
}


my $metadata_before_backup=qx(ls -l $data_dir $tokudb_log_dir/*);
##### STEP 3. get checkpoint lock 
#set tokudb_checkpoint_lock=on:let dml only change redo log
$row_ref=$dbh->selectrow_arrayref("select * from information_schema.global_variables where variable_name='tokudb_checkpoint_lock'");
print $debug_log "global:$row_ref->[0]:$row_ref->[1]\n";
$row_ref=$dbh->selectrow_arrayref("select * from information_schema.session_variables where variable_name='tokudb_checkpoint_lock'");
print $debug_log "session:$row_ref->[0]:$row_ref->[1]\n";
$dbh->do("SET TOKUDB_CHECKPOINT_LOCK=ON;") or die "Get tokudb_checkpoint lock failed";
print $debug_log qx(date);
$row_ref=$dbh->selectrow_arrayref("select * from information_schema.global_variables where variable_name='tokudb_checkpoint_lock'");
print $debug_log "global:$row_ref->[0]:$row_ref->[1]\n";
$row_ref=$dbh->selectrow_arrayref("select * from information_schema.session_variables where variable_name='tokudb_checkpoint_lock'");
print $debug_log "session:$row_ref->[0]:$row_ref->[1]\n";
print $debug_log "set tokudb_checkpoint_lock=on ok\n\n";


##### STEP 4. Copy tokudb.* and redo log, and get binlog position in a blocking-binlog or stopping-slave; 
if(defined $dump_slave){
    $dbh->do("set \@old_rpl_stop_slave_timeout=\@\@rpl_stop_slave_timeout;") or die("failed to get the value of rpl_stop_slave_timeout");
    print($debug_log "rpl_stop_slave_timeout:".(($dbh->selectrow_arrayref("select \@\@rpl_stop_slave_timeout"))->[0])."\n");
    $dbh->do("set global rpl_stop_slave_timeout=10;") or die("failed to set the value of rpl_stop_slave_timeout");
    print($debug_log qx(date));
    my $ret=$dbh->do("stop slave;");
    print($debug_log qx(date)."\n");
    $dbh->do("set global rpl_stop_slave_timeout=\@old_rpl_stop_slave_timeout;") or die("failed to recover the value of rpl_stop_slave_timeout");
    if(not defined $ret){#Assuming that there are dead locks,and stop slave time out
	my $dbh = DBI->connect ("DBI:mysql:mysql:host=$host:port=$port:mysql_socket=$sock", $user, $password);
	$ret=qx(mysql -h $host -P $port -u$user -p$password -e "show full processlist") or die "failed to execute 'show full processlist':$!";
	print($debug_log $ret);
        $dbh->do("SET TOKUDB_CHECKPOINT_LOCK=OFF;") or die "release tokudb_checkpoint lock failed";
        system("rm -rf $backdir/mysql_data")==0 or die "failed:$!";
        close $debug_log;
        close $backed_debug_log;
        exit(223); 
    }
    print $debug_log qx(date);
    print $debug_log "stop slave ok\n\n";
}else{
    $dbh->do("lock binlog for backup;") or die "lock binlog for backup failed";
    print $debug_log qx(date);
    print $debug_log "lock binlog for backup ok\n\n";
}

print $backed_debug_log "Binlog time: " . qx(date)."\n";
print $debug_log "Binlog time: " . qx(date)."\n";
my $binlog_stamp=time;

print $debug_log qx(date);
print $debug_log "copy tokudb redolog in: $tokudb_log_dir ...";
system("ls $tokudb_log_dir| xargs -I '{}' cp -r $tokudb_log_dir/{} $backdir/tokudb_log")==0 or die "failed:$!\n";
print $debug_log "\tdone.\n";
print $debug_log qx(date)."\n";

print $debug_log qx(date);
print $debug_log "copy tokudb rollback log ...";
system("ls $data_dir/tokudb.*| xargs -I '{}' cp -r {}  $backdir/")==0 or die "failed:$!";
print $debug_log "\tdone.\n";
print $debug_log qx(date)."\n";

#get tokudb_data list
my @tokudb_data_files;
open FILELIST,">$backdir/tokudb_data/filelist.txt" or die "can't open $backdir/tokudb_data/filelist.txt:$!\n";
my $select_file=$dbh->prepare("select distinct internal_file_name from information_schema.TokuDB_file_map");
$select_file->execute();
while(my @tokudb_files=$select_file->fetchrow_array){
    push(@tokudb_data_files,$tokudb_files[0]);
    printf(FILELIST "$tokudb_files[0]\n"); 
}
close FILELIST;

$sql = qq{show master status};
$row_ref     = $dbh->selectrow_hashref($sql);
if(defined $row_ref and defined $row_ref->{'File'} and defined $row_ref->{'Position'} ){
    open(my $master_info, ">", "$backdir/xtrabackup_binlog_info") or die "could not open binlog_info file\n";
    print $master_info "$row_ref->{'File'}  $row_ref->{'Position'}\n";
    close $master_info;
}else{
    die "Get master info failed\n";
}

if(defined $dump_slave){
    $sql = qq{show slave status};
    $row_ref     = $dbh->selectrow_hashref($sql);
    if (defined $row_ref and defined $row_ref->{'Relay_Master_Log_File'} and defined $row_ref->{'Exec_Master_Log_Pos'})
    {
	open(my $slave_info, ">", "$backdir/xtrabackup_slave_info") or die "could not open slave_info file";
	print $slave_info "CHANGE MASTER TO MASTER_LOG_FILE='$row_ref->{Relay_Master_Log_File}', MASTER_LOG_POS=$row_ref->{'Exec_Master_Log_Pos'} \n";
	close $slave_info;
    }else{
	die "Get salve info failed\n";
    }
}

print $debug_log qx(date);
print $debug_log "copy mysql configure file: $myconf ...";
system("cp $myconf  $backdir/backup-my.cnf") ==0 or die "failed:$!\n";
print $debug_log "\tdone.\n";
print $debug_log qx(date)."\n";

if(defined $dump_slave){
    $dbh->do("start slave") or die "start slave faild\n";
    print $debug_log qx(date);
    print $debug_log "start slave ok,time:".(qx(date))."\n";
}else{
    $dbh->do("unlock binlog") or die "start slave faild\n";
    print $debug_log qx(date);
    print $debug_log "unlock binlog ok,time:".(qx(date))."\n";
}


##### STEP 5. Copy frm
## no flush table with read lock ???
print $debug_log qx(date);
print $debug_log "copy mysql data dir: $data_dir/ ...";
system("ls $data_dir| xargs -I '{}' cp -r $data_dir/{}  $backdir/mysql_data")==0 or die "failed:$!";

print $debug_log qx(date);
print $debug_log "copy innodb ibdata1 in: $innodb_home_dir ...";
system("cp -r $innodb_home_dir $backdir/innodb_data/")==0 or die "failed:$!\n";
system("cp -r $innodb_log_dir $backdir/innodb_data/")==0 or die "failed:$!\n";

print $debug_log "\tdone.\n";
print $debug_log qx(date)."\n";

##### STEP 6. recovery tokudb_commit_sync; 
#$ret=$dbh->do("set global tokudb_commit_sync=$old_global_tokudb_commit_sync");
#die "unable to restore tokudb_commit_sync" if not defined $ret or $ret<0;
##sleep(100);
#print qx(date);
#print "enable tokudb redo log buffer ok\n\n";
#
#goto SKIP;
##### STEP 7. copy data or increment data 
if(is_low_space("$Bin/history_backup_size","$Bin/last_backup_size",$backdir,0.96,$debug_log)){
    push(@tokudb_backup_warnings,"SMS#low space,previous file for port:${port} will be deleted,and a fully backup will be done today");
    #delete old file
    print $debug_log "\tlow space,delete old file and then fully backup";
    qx(ls $backdir|grep _${port}_|grep _${host}_|xargs rm -rf);
    #fully backup
    foreach my $file(@tokudb_data_files){
        system("cp -r $tokudb_data_dir/$file $backdir/tokudb_data") ==0 or die "copy $tokudb_data_dir/$file to $backdir/tokudb_data failed:$!";
    }
}elsif(not $increment){
	print $debug_log qx(date);
    print $debug_log "fully copy tokudb data dir: $tokudb_data_dir/ ...";
    foreach my $file(@tokudb_data_files){
        system("cp -r $tokudb_data_dir/$file $backdir/tokudb_data") ==0 or die "copy $tokudb_data_dir/$file to $backdir/tokudb_data failed:$!";
    }
    #system("ls $tokudb_data_dir|xargs -I '{}' cp -r $tokudb_data_dir/{} $backdir/tokudb_data") ==0 or die "failed";
}else{
	print $debug_log qx(date);
    print $debug_log "incrementally backup($tokudb_data_dir/)";
    my($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst)=localtime(time()+$global_time_offset);
    if(($port%7)==$wday){   #default fully backup day,20000%7=1
        print $debug_log "\tfully day";
        foreach my $file(@tokudb_data_files){
            system("cp -r $tokudb_data_dir/$file $backdir/tokudb_data") ==0 or die "copy $tokudb_data_dir/$file to $backdir/tokudb_data failed:$!";
        }
        #system("ls $tokudb_data_dir|xargs -I '{}' cp -r $tokudb_data_dir/{} $backdir/tokudb_data") ==0 or die "failed";
    }else{
#1 get the fully backup up info file
        print $debug_log "\tincremental day";
        opendir (DIR,$dir) or die "can't open the directory $dir";
        my @dirs=readdir DIR;
        close DIR;
        
        #my $fully_backup_port=$wday;
        #while($fully_backup_port<$port){$fully_backup_port+=7;}
        #my $days_since_fully=$fully_backup_port-$port;

# time = strftime("%Y%m%d_%H%M%S", localtime(time));
# target_name = "${app_name}_${hostname}_${host_address}_${port}_${time}";
# fully day info file name should be: \S+_${host}_${port}_${fullyday}_\d{6}\.info
        #print "\tport:$port fully_backup_port:$fully_backup_port days_since_fully:$days_since_fully";
        my $tmpstamp;
        my $tmpname;
        my $i;
        my $fully_stamp_and_name={};
        for($i=0;$i<7;$i++){
            my $fullyday=strftime("%Y%m%d", localtime($fully_stamp-$i*24*3600)); 
            #print "\$port:$port \$fully_backup_port:$fully_backup_port \$days_since_fully:$days_since_fully \$fullyday:$fullyday\n";
            #print "now begin to exam ".(scalar @dirs)." file\n";
            foreach my $file(@dirs){
                chomp($file);
                if($file =~ /(\S+_${port}_${fullyday}_\d{6}_TOKUDB_INCREASE)\.info$/){
                    my $current_name=$1;
                    open INFO,"<$dir/$file" or print $debug_log "unable to open $dir/$file",last;
                    #print "\nexaming file: $file\n";
                    while(<INFO>){
                        chomp;
                        my $tmpstr=$_;
                        if($tmpstr =~ /\s*FULLY_STAMP\s*=\s*(\d+)/){
                            $tmpstamp=$1;
                        }elsif($tmpstr=~/\s*FULLY_NAME\s*=\s*(\S+)/){
                            $tmpname=$1;
                        }
                    }
                    close INFO;
                    if(defined $tmpstamp and defined $tmpname and $tmpname eq $current_name){#find fully backup info file
                        $fully_stamp_and_name->{$tmpstamp}=$tmpname;                
                    }
                    $tmpstamp=undef;
                    $tmpname=undef;#for multi fully backup one day
                }
            }
            if(scalar keys %$fully_stamp_and_name){
                last;
            }
        }
        my @fully_stamps=sort keys %$fully_stamp_and_name;
        if(@fully_stamps){  #previous backup is ok
            print $debug_log "\tincremental backup";
            $fully_stamp=$fully_stamps[-1];
            $fully_name=$fully_stamp_and_name->{$fully_stamp};
            print $debug_log "\nfully_stamp:$fully_stamp\nfully_name:$fully_name\n";
            foreach my $file(@tokudb_data_files){
                my($device, $inode, $mode, $nlink, $uid, $gid, $rdev, $size,$atime, $mtime, $ctime, $blksize, $blocks) = stat("$tokudb_data_dir/$file");
                #printf("$file\tmtime:$mtime($fully_stamp)\tctime:$ctime($fully_stamp)\n");
                if($mtime>$fully_stamp ||($ctime>$fully_stamp)){
                    system("cp  $tokudb_data_dir/$file  $backdir/tokudb_data") ==0 or die "failed:$!";
                    #printf("copied $file\n");
                }
            } 
        }else{  #previous backup failed
            #print "\tfully backup(i:$i fully_stamp:$fully_stamp)";
            print $backed_debug_log "\ttmpstamp:$tmpstamp" if defined $tmpstamp;
            print $debug_log "\ttmpstamp:$tmpstamp" if defined $tmpstamp;
            foreach my $file(@tokudb_data_files){
                system("cp -r $tokudb_data_dir/$file $backdir/tokudb_data") ==0 or die "copy $tokudb_data_dir/$file to $backdir/tokudb_data failed:$!";
            }
            #system("ls $tokudb_data_dir|xargs -I '{}' cp -r $tokudb_data_dir/{} $backdir/tokudb_data") ==0 or die "failed";
        }
    }
}
SKIP:
print $debug_log "\tdone.\n";
print $debug_log qx(date)."\n";

##### STEP 8. check file change time 
my $metadata_after_backup=qx(ls -l $data_dir $tokudb_log_dir/*);
print $backed_debug_log "############################################# metadata before backup ######################################################\n";
print $backed_debug_log $metadata_before_backup;
print $backed_debug_log "############################################# metadata after backup  ######################################################\n";
print $backed_debug_log $metadata_after_backup;
print $debug_log "############################################# metadata before backup ######################################################\n";
print $debug_log $metadata_before_backup;
print $debug_log "############################################# metadata after backup  ######################################################\n";
print $debug_log $metadata_after_backup;
#begin check that all file's ctime should not be new than $binlog_stamp
my @changed_file;
opendir (DIR,$tokudb_data_dir) or die "can't open the directory $dir";
my @dirs=readdir DIR;
close DIR;
print $backed_debug_log "#################################################### changed file ###########################################################\n";
print $debug_log "#################################################### changed file ###########################################################\n";
foreach my $file(@dirs){
    if($file eq "\." or $file eq "\.\."){next;}
    my($device, $inode, $mode, $nlink, $uid, $gid, $rdev, $size,$atime, $mtime, $ctime, $blksize, $blocks) = stat("$tokudb_data_dir/$file");
    if($mtime>$binlog_stamp){
	my $full_file_path="$tokudb_data_dir/$file";
	my $ls_l_of_file=qx(ls -l --time-style='+%Y-%m-%d %H:%M:%S' $full_file_path);
	my $adate=strftime("%Y-%m-%d %H:%M:%S", localtime($atime));
	my $mdate=strftime("%Y-%m-%d %H:%M:%S", localtime($mtime));
	my $cdate=strftime("%Y-%m-%d %H:%M:%S", localtime($ctime));
	my $bdate=strftime("%Y-%m-%d %H:%M:%S", localtime($binlog_stamp));
	chomp($ls_l_of_file);
	print $backed_debug_log "$ls_l_of_file\tchanged:a($adate) m($mdate) c($cdate) b($bdate)\n";
	print $debug_log "$ls_l_of_file\tchanged:a($adate) m($mdate) c($cdate) b($bdate)\n";
        #print "$tokudb_data_dir/$file changed\n";
        push(@changed_file,"$tokudb_data_dir/$file");
    }
}

##### STEP 9. release metadata lock 
if($tmysql_ver ge tmysql_version_parser("tmysql-2.1.3")){
    $dbh->do("unlock tables") or die "failed to release metadata lock";
    print $debug_log qx(date);
    print $debug_log "release all metadata lock ok\n\n";
}


##### STEP 10. release tokudb_checkpoint_lock 
$dbh->do("SET TOKUDB_CHECKPOINT_LOCK=OFF") or die "release tokudb checkpoint lock failed";
$row_ref=$dbh->selectrow_arrayref("select * from information_schema.global_variables where variable_name='tokudb_checkpoint_lock'");
print $debug_log "global:$row_ref->[0]:$row_ref->[1]\n";
$row_ref=$dbh->selectrow_arrayref("select * from information_schema.session_variables where variable_name='tokudb_checkpoint_lock'");
print $debug_log "session:$row_ref->[0]:$row_ref->[1]\n";
print $debug_log qx(date);
print $debug_log "set tokudb_checkpoint_lock=off ok\n\n";
$dbh->disconnect;


##### STEP 11. fully backup info to file 
#save fully backup info to file
open my $latest_fully_backup_info,">$Bin/latest_fully_backup_info.$port" 
or die("ERROR: Can not open latest fully backup info file $Bin/latest_fully_backup_info.$port for $@");
printf $latest_fully_backup_info "FULLY_STAMP=$fully_stamp\n";
printf $latest_fully_backup_info "FULLY_NAME=$fully_name\n";
close($latest_fully_backup_info);
if(scalar @changed_file){
    #print "changed file:".(join(',',@changed_file))."\n";
    my $file_string=join(",",@changed_file);
    print $backed_debug_log "changed file:$file_string\n";
    print $debug_log "changed file:$file_string\n";
    push(@tokudb_backup_warnings,"INFO#warning:some file changed during backup,see more information in $debug_log_file");
}
if(scalar @other_engines){
    my $other_engine_string=join(",",@other_engines);
    my $backup_databases_string=join(",",@backup_databases);
    push(@tokudb_backup_warnings,"SMS#engine other than tokudb exists, other engine:$other_engine_string database:$backup_databases_string");
    print "warning:engine other than tokudb($other_engine_string) exists in $backup_databases_string\n";
}
print_log("$Bin/tokudb_backup.log.$port",@tokudb_backup_warnings);
close $backed_debug_log;
close $debug_log;
#system("date '+%s'> $backdir/TOKUDB.END");
$date=strftime("%Y%m%d_%H%M%S", localtime(time()+$global_time_offset));
system("echo $date >> $backdir/TOKUDB.END");

sub print_log{
#logarray entry format:level#message
    my($logfile,@logarray)=@_;
    if(scalar @logarray){
        open LOG,">$logfile" or die "unable to open $logfile";
        foreach my $log(@logarray){
            print LOG $log;
        }
        close LOG;
    }else{
        if(-e $logfile){
            system("rm $logfile")==0 or print "WARNING:failed to rm previous logfile:$logfile:$!\n";
        }
    }
}
sub get_history_max_backup_size{
    my($history_file)=@_;
    if(-e $history_file and -r $history_file){
        my $max=qx(cat $history_file|grep _${port}_|tail -7|awk '{print \$2}'|sort -n|tail -1);
        chomp($max) if defined $max;
        if(defined $max and $max=~/\d+/){
            return $max;
        }else{
            return 0;
        }
    }else{
        return 0;
    }
}
sub is_low_space{
    my($history_file,$last_file,$backup_dir,$max_percent,$debug_log)=@_;
    my $max_size=get_history_max_backup_size($history_file);
    my $last_size=get_history_max_backup_size($last_file);
    my $max=($max_size>$last_size)?$max_size:$last_size;
    if($max==0){
        return 0;
    }else{
        my $backup_disk = (split(/\//, $backup_dir))[1];
        my $disk_total = qx#df -P /$backup_disk | sed '1d' | awk '{print \$2}'#;
        my $disk_used  = qx#df -P /$backup_disk | sed '1d' | awk '{print \$3}'#;
        chomp $disk_total;       #in kB
        chomp $disk_used;       #in kB
        $disk_total *= 1024;     #to Byte
        $disk_used *= 1024;     #to Byte
        my $space_may_used=$disk_used+$max;
        my $warn_level=$disk_total*$max_percent;
        print $debug_log "total-space:${disk_total}B used-space:${disk_used}B backup-may-use:${max}B warn-level:${warn_level}B \n";
        if($space_may_used>$warn_level){ 
            print $debug_log "use-space + space-backup-may-use=${space_may_used}B > warn_level=${warn_level}B\n";
            return 1;
        }else{
            print $debug_log "use-space + space-backup-may-use=${space_may_used}B <= warn_level=${warn_level}B\n";
            return 0;
        }
    }
}
