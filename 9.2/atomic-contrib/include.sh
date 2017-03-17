# Check whether all required variables are set
if ! [ -v NAME -a -v IMAGE -a -v HOST ] ; then
  echo "Environment variables NAME, IMAGE and HOST must be set."
  exit 1
fi

# Define well-known directories and names on the host
service_name="${NAME}"
data_dir="/var/lib/${service_name}"

# We don't want to use LD_PRELOAD here, we usually run this script as root
unset LD_PRELOAD

