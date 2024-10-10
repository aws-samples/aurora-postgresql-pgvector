!/bin/bash
# Install necessary packages
sudo yum update -y
sudo yum install -y git python3 python3-pip postgresql
# Set up environment variables
echo "export DB_CLUSTER_IDENTIFIER=${DB_CLUSTER_IDENTIFIER}" >> ~/.bashrc
echo "export DEFAULT_CODE_REPO=${DEFAULT_CODE_REPO}" >> ~/.bashrc
echo "export SECRETARN=${SECRETARN}" >> ~/.bashrc
echo "export AWSREGION=${AWSREGION}" >> ~/.bashrc
# Get DB Endpoint
DBENDP=$(aws rds describe-db-clusters --db-cluster-identifier $DB_CLUSTER_IDENTIFIER --region $AWSREGION --query 'DBClusters[*].Endpoint' | jq -r '.[0]')
echo "export DBENDP=$DBENDP" >> ~/
# Get database credentials
CREDS=$(aws secretsmanager get-secret-value --secret-id $SECRETARN --region $AWSREGION | jq -r '.SecretString')
DBUSER=$(echo $CREDS | jq -r '.username')
DBPASS=$(echo $CREDS | jq -r '.password')
echo "export PGHOST=$DBENDP" >> ~/.bashrc
echo "export PGUSER=$DBUSER" >> ~/.bashrc
echo "export PGPASSWORD=$DBPASS" >> ~/.bashrc
echo "export PGDATABASE=postgres" >> ~/.bashrc
# Create a .pgpass file for passwordless login
echo "$DBENDP:5432:postgres:$DBUSER:$DBPASS" > ~/.pgpass
chmod 600 ~/.pgpass
# Clone the default code repository
git clone $DEFAULT_CODE_REPO ~/code-repo
# Source the updated .bashrc
source ~/.bashrc
# Print completion message
echo "Cloud9 environment setup completed successfully."
