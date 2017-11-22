FROM tiangolo/uwsgi-nginx-flask:python2.7

# copy over our requirements.txt file
COPY requirements.txt /tmp/

# upgrade pip and install required python packages
RUN pip install -U pip
RUN pip install -r /tmp/requirements.txt

# Copy the current directory contents into theh container at /app
COPY ./app /app

# Make kops accessible
COPY ./bin/kops /usr/local/bin/kops
RUN chmod +x /usr/local/bin/kops