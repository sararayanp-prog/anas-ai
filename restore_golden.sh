#!/bin/bash
cd ~/anas-ai
git checkout backup-v12-golden 2>/dev/null || git checkout v12.0-golden-master
echo '✅ Restored to Golden Master v12.0!'
