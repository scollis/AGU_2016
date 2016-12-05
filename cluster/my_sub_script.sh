#!/bin/bash
#PBS -l nodes=4:ppn=12
#PBS -l walltime=00:10:00
#PBS -j oe
#PBS -V
#PBS -N IPythonMPI0

#source activate radar35
export LD_LIBRARY_PATH=/home/scollis/coin/lib/:$LD_LIBRARY_PATH
ipcluster start --n=12 --profile=mpi0

