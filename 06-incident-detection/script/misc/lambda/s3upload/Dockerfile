FROM --platform=linux/x86_64 public.ecr.aws/lambda/python:3.9
RUN yum -y install openssl \
    coreutils \
    tar \
    wget \
    gzip
COPY app.py requirements.txt ./
RUN pip3 install -r requirements.txt 
# Command can be overwritten by providing a different command in the template directly.
CMD ["app.lambdaHandler"]
