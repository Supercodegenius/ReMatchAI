#!/bin/bash

# ----------------------------------------
# CONFIGURATION
# ----------------------------------------
LOCAL_SOURCE_DIR="/c/Python/AIPoweredNameMatching/Source"
REMOTE_USER="braincalre"
REMOTE_HOST="rematchingai.com"
REMOTE_SOURCE_DIR="/home/braincalre/apps/name-matching/app/Source"

echo "----------------------------------------"
echo " 🚀 ReMatch Deployment Started"
echo "----------------------------------------"

# ----------------------------------------
# STEP 1 — Deploy Source folder
# ----------------------------------------
echo "📁 Syncing Source folder..."
scp -r "$LOCAL_SOURCE_DIR"/*.py $REMOTE_USER@$REMOTE_HOST:$REMOTE_SOURCE_DIR/

if [ $? -ne 0 ]; then
    echo "❌ ERROR: Failed to sync Source folder"
    exit 1
fi

# ----------------------------------------
# STEP 2 — Deploy assets folder
# ----------------------------------------
echo "📁 Syncing assets folder..."
scp -r "$LOCAL_SOURCE_DIR/assets"/* $REMOTE_USER@$REMOTE_HOST:$REMOTE_SOURCE_DIR/assets/

if [ $? -ne 0 ]; then
    echo "❌ ERROR: Failed to sync assets folder"
    exit 1
fi

# ----------------------------------------
# STEP 3 — Restart Streamlit (optional)
# ----------------------------------------
echo "🔄 Restarting Streamlit app on VPS..."
ssh $REMOTE_USER@$REMOTE_HOST "pkill -f streamlit; nohup streamlit run /home/braincalre/apps/name-matching/app/streamlit_app.py --server.port 8501 --server.address 0.0.0.0 >/dev/null 2>&1 &"

echo "----------------------------------------"
echo " ✅ Deployment Complete"
echo "----------------------------------------"
