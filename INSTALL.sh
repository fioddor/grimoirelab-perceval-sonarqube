#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Purpose: Deploy grimoirelab-perceval-sonarqube backend.
# Usage..: Needs superpowers.
# Design.: Not really designed.
# Authors: Igor Zubiaurre <izubiaurre@bitergia.com>
# Pending: Design properly:
#          - Configuration file should be placed and searched elsewhere.
#          - Pack for PIP.
#

SRC_DIR=perceval/backends/sonarqube
LIB_DIR=lib/python3.9

# Alternative installations
YOU=YOUR_USER_NAME_HERE
DEB_USR=/home/$YOU/.local/$LIB_DIR/site-packages/$SRC_DIR   # User install on Debian
DEB_SYS=/usr/local/$LIB_DIR/dist-packages/$SRC_DIR          # System install on Debian

BIN_DIR=$DEB_SYS                                            # Choose the alternative
CFG_DIR=$BIN_DIR

# Deploy

cp $SRC_DIR/__init__.py   $BIN_DIR/
cp $SRC_DIR/sonarqube.py  $BIN_DIR/
echo "Binaries deployed to $BIN_DIR"

CFG=sonarqube.cfg
if [ -f $CFG_DIR/$CFG ]
then
    echo "Check configuration at $CFG_DIR/$CFG"
else
    cp $SRC_DIR/$CFG $CFG_DIR/
    echo "Configuration deployed to $CFG_DIR as $CFG"
fi
