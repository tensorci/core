FROM tiangolo/uwsgi-nginx-flask:python2.7

# Copy requirements.txt file into container's tmp dir.
COPY requirements.txt /tmp/

# Upgrade pip and install required python packages.
RUN pip install -U pip
RUN pip install -r /tmp/requirements.txt

# Copy app/ contents into container.
COPY app /app

# Copy migrations dir into /app
COPY migrations /app/migrations

# Make kops command accessible.
COPY ./bin/kops /usr/local/bin/kops
RUN chmod +x /usr/local/bin/kops

# Make kubectl command accessible.
COPY ./bin/kubectl /usr/local/bin/kubectl
RUN chmod +x /usr/local/bin/kubectl

# Generate id_rsa ssh key for kops to use.
# It will check for /root/.ssh/id_rsa.pub
RUN ssh-keygen -f /root/.ssh/id_rsa -t rsa -N ''

# Make our startup script executable.
RUN chmod +x /app/startup

# Copy and set entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# Start the app
CMD ["/app/startup"]