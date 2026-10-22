FROM rocker/rstudio:4.4.2

RUN apt-get update && apt-get install -y curl gnupg unixodbc-dev \
 && curl -sSL https://packages.microsoft.com/keys/microsoft.asc \
    | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
 && . /etc/os-release \
 && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/ubuntu/${VERSION_ID}/prod ${VERSION_CODENAME} main" \
    > /etc/apt/sources.list.d/mssql-release.list \
 && apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
 && rm -rf /var/lib/apt/lists/*

RUN install2.r --error --skipinstalled \
    tidyverse DBI odbc broom pROC randomForest xgboost
