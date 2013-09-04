# install Dependencie
SITE_PKG_DIR=$VIRTUAL_ENV/lib/python$TRAVIS_PYTHON_VERSION/site-packages
echo "Using SITE_PKG_DIR: $SITE_PKG_DIR"

# workaround for travis ignoring system_site_packages in travis.yml
rm -f $VIRTUAL_ENV/lib/python$TRAVIS_PYTHON_VERSION/no-global-site-packages.txt

# For pytables
sudo apt-get install libhdf5-serial-dev hdf5-tools
# For numpy/scipy
sudo apt-get install -qq gfortran swig liblapack-dev libzmq-dev
sudo apt-get install -qq libatlas-base-dev libjpeg-dev libhdf5-serial-dev
sudo apt-get install -qq liblzo2-dev libsuitesparse-dev
# For matplotlib
sudo apt-get install -qq libpng12-dev libfreetype6-dev tk-dev
sudo apt-get install python-numpy
sudo apt-get install python-scipy
sudo apt-get install python-matplotlib

pip install numexpr # prereq for tables
pip install cython  # prereq for tables