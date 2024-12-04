#!/usr/bin/perl

use FindBin qw($Bin);

use warnings;
use strict;
use Getopt::Long qw(:config posix_default);
use POSIX qw(strftime);
use File::Basename;
use Data::Dumper;
use DBI;


my $backdir= undef;
my $myconf = undef;
my $increment=0;

my @normal_dbs = ("mysql", "test", "performance_schema", "db_infobase", "sys");

Getopt::Long::Configure ("bundling_override");
GetOptions(
	'backup-path=s'    => \$backdir,
	'defaults-file=s'  => \$myconf,
    'increment|i!'  => \$increment
)or die "usage: xxx --backup-path={path} --defaults=file={path} [<-i|increment> <fully-backup-file-dir>]";


unless (defined $backdir && defined $myconf){
    die "back-path or defaults-file undefined";
}

die "$backdir is not a dir" unless( -d $backdir);
my $fully_dir=undef;
if($increment){
    die "when enable increment, fully-backup-file-dir is needed!" unless(@ARGV==1);
    die "$ARGV[0] is not a dir" unless(-d $ARGV[0]);
    $fully_dir=$ARGV[0];
}
my $data_dir        = undef;
my $tokudb_data_dir = undef;
my $tokudb_log_dir  = undef;

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
}
close($my_cnf_fp);

unless (defined $data_dir &&
        defined $tokudb_data_dir &&
        defined $tokudb_log_dir )
{
    die "some key in $myconf lost";
}

system("ls $backdir/tokudb_log|xargs -I '{}' cp -r $backdir/tokudb_log/{} $tokudb_log_dir") == 0 or die "failed";
if($increment){
    if(!open FILELIST,"<$backdir/tokudb_data/filelist.txt"){
            die "open filelist.txt failed";
    }
    while(<FILELIST>){
        chomp;
        my $file=$_;
        if(-e "$backdir/tokudb_data/$file"){
            $file="$backdir/tokudb_data/$file";
        }else{
            die "can't find $file in both $backdir/tokudb_data and $fully_dir/tokudb_data" unless(-e ($file="$fully_dir/tokudb_data/$file"));
        }
        system("cp $file $tokudb_data_dir") == 0 or die "failed";
    }
}else{
    eval{system("ls $backdir/tokudb_data |xargs -I '{}' cp -r $backdir/tokudb_data/{} $tokudb_data_dir")}; die $@ if $@;
}
system("ls $backdir/tokudb.*|xargs -I '{}' cp {} $data_dir") == 0 or die "failed";

foreach my $file (glob("$backdir/mysql_data/*/")){
    my $tmp_file=basename($file);
    if(not grep(/$tmp_file/,@normal_dbs) ){
        print "copy database: $tmp_file\n";
        system("cp -r $file  $data_dir") == 0 or die "failed";
    }
}