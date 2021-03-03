#!/bin/bash

sourcecode_subdir_name="sourcecode"
dunedaq_release_version="v2.2.0"

current_subdir=`echo ${PWD} | xargs basename`
#echo "cwd = ${current_subdir}"

# First, check if dbt-create.sh needs to be run.
# If the dbt-create script can't be found, we simply go on to the parts that we *can* do.
dbt_create_path=`which dbt-create.sh`
if [[ "$dbt_create_path" != "" ]]; then
    if [[ "$current_subdir" != "$sourcecode_subdir_name" ]]; then
        if [[ ! -d "$sourcecode_subdir_name" ]]; then
            echo ""
            echo "*** It appears that dbt-create.sh has not yet been run in the current directory."
            echo "*** (current working directory = \"$PWD\")"
            echo "*** Do you want to run it now (y/n/a [default is \"a\" for \"abort this script\"])"
            read response
            if [[ "$response" == "y" ]]; then
                dbt-create.sh dunedaq-${dunedaq_release_version}
            elif [[ "$response" == "n" ]]; then
                echo "Skipping dbt-create..."
            else
                return 1
            fi
        fi
    fi
fi

# Next, verify that we're in a good location to do the repo clones
if [[ "$current_subdir" != "$sourcecode_subdir_name" ]]; then
    if [[ -d "$sourcecode_subdir_name" ]]; then
        cd ${sourcecode_subdir_name}
    else
        echo "*** Warning: this script needs to be run in a newly-created dunedaq software area."
        echo "*** Warning: unable to find a subdirectory named \"${sourcecode_subdir_name}\", exiting."
        return 1
    fi
fi

# Define a function to handle the clone of a single repo.
# There are two required arguments: repo name and initial branch.
# A third, optional, argument is a commit hash or tag to checkout.
function clone_repo_for_mdapp {
    if [[ $# -lt 2 ]]; then
        return 1
    fi
    git clone https://github.com/DUNE-DAQ/${1}.git -b ${2}
    if [[ $# -gt 2 ]]; then
        cd ${1}
        git checkout ${3}
        cd ..
    fi
}

# Clone the repos that we want
clone_repo_for_mdapp daq-cmake develop v1.3.1
clone_repo_for_mdapp ers v1.1.0
clone_repo_for_mdapp logging develop v1.0.0
clone_repo_for_mdapp cmdlib develop v1.1.1
clone_repo_for_mdapp rcif develop v1.0.1
clone_repo_for_mdapp appfwk develop v2.2.0
clone_repo_for_mdapp dataformats develop
clone_repo_for_mdapp dfmessages develop
clone_repo_for_mdapp dfmodules develop
clone_repo_for_mdapp flxlibs develop
clone_repo_for_mdapp ipm develop
clone_repo_for_mdapp nwqueueadapters develop
clone_repo_for_mdapp opmonlib develop v1.0.0
clone_repo_for_mdapp readout develop
clone_repo_for_mdapp restcmd develop
clone_repo_for_mdapp serialization develop
clone_repo_for_mdapp trigemu develop
clone_repo_for_mdapp minidaqapp develop

# Next, update the dbt-build-order.cmake file
cp -p dbt-build-order.cmake dbt-build-order.cmake.orig
sed -i 's/"daq-cmake" "logging"/"daq-cmake" "ers" "logging"/' dbt-build-order.cmake
sed -i 's/"restcmd" "appfwk"/"restcmd" "opmonlib" "appfwk"/' dbt-build-order.cmake
sed -i 's/"ipm" "dataformats"/"ipm" "serialization" "nwqueueadapters" "dataformats"/' dbt-build-order.cmake
sed -i 's/"cmdlib" "restcmd"/"cmdlib" "rcif" "restcmd"/' dbt-build-order.cmake
sed -i 's/"readout" "trigemu"/"readout" "flxlibs" "trigemu"/' dbt-build-order.cmake

# Next, update the dbt-settings file
cd ..
cp -p dbt-settings dbt-settings.orig
sed -i 's,#"/cvmfs/dune.opensciencegrid.org/dunedaq/DUNE/products","/cvmfs/dune.opensciencegrid.org/dunedaq/DUNE/products",' dbt-settings
sed -i 's,#"/cvmfs/dune.opensciencegrid.org/dunedaq/DUNE/products_dev","/cvmfs/dune.opensciencegrid.org/dunedaq/DUNE/products_dev",' dbt-settings
sed -i 's/"zmq v4_3_1b e19"/"zmq v4_3_1c e19:prof"\n    "cppzmq v4_3_0 e19:prof"\n    "msgpack_c v3_3_0 e19:prof"\n    "felix v1_1_1 e19:prof"/' dbt-settings

# Lastly, setup the build environment and update the version of moo
dbt-setup-build-environment
pip uninstall moo && pip install https://github.com/brettviren/moo/archive/0.5.5.tar.gz
