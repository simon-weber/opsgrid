let
  duplKey = builtins.readFile ../secrets/pydriveprivatekey.pem;
  opsgridToken = builtins.readFile ../secrets/opsgrid_token.txt;
  webNRKey = builtins.readFile ../secrets/web_new_relic_key.txt;
  ingestNRKey = builtins.readFile ../secrets/ingest_new_relic_key.txt;
  dbPath = "/opt/opsgrid-web/opsgrid-web_db.sqlite3";
  logUnitYaml = lib: builtins.toJSON (lib.lists.flatten (builtins.map (x: [ "UNIT=${x}" "_SYSTEMD_UNIT=${x}" ]) [
    "acme-sheets.simon.codes.service"
    "acme-www.opsgrid.net.service"
    "duplicity.service"
    "docker.service"
    "docker-sheets.service"
    "docker-opsgrid-web.service"
    "nginx.service"
    "sshd.service"
  ]));
in let
  genericConf = { config, pkgs, lib, ... }: {
    virtualisation.docker = {
      enable = true;
      logDriver = "journald";
    };
    docker-containers.opsgrid-ingest = {
      image = "opsgrid-ingest:latest";
      ports = [ "127.0.0.1:8001:8001" ];
      volumes = [ "/opt/opsgrid-ingest:/opt/opsgrid-ingest" ];
      environment = {
        NEW_RELIC_LICENSE_KEY = webNRKey;
        NEW_RELIC_PROCESS_HOST_DISPLAY_NAME = "golf.simon.codes";
      };
    };
    docker-containers.opsgrid-web = {
      image = "opsgrid-web:latest";
      ports = [ "127.0.0.1:8000:8000" ];
      volumes = [ "/opt/opsgrid-web:/opt/opsgrid-web" ];
      environment = {
        NEW_RELIC_LICENSE_KEY = webNRKey;
        NEW_RELIC_PROCESS_HOST_DISPLAY_NAME = "golf.simon.codes";
      };
    };
    docker-containers.opsgrid-web_cleanup = {
      image = "opsgrid-web:latest";
      volumes = [ "/opt/opsgrid-web:/opt/opsgrid-web" ];
      entrypoint = "python";
      cmd = [ "manage.py" "clearsessions" ];
    };
    systemd.services.docker-opsgrid-web_cleanup = {
      startAt = "*-*-* 07:30:00";
      wantedBy = pkgs.lib.mkForce [];
      serviceConfig = {
        Restart = pkgs.lib.mkForce "no";
        ExecStopPost = pkgs.lib.mkForce [ "-${pkgs.docker}/bin/docker rm -f %n" "${pkgs.sqlite}/bin/sqlite3 ${dbPath} 'VACUUM;'" ];
      };
    };

    services.nginx = {
      enable = true;
      recommendedGzipSettings = true;
      recommendedOptimisation = true;
      recommendedProxySettings = true;
      recommendedTlsSettings = true;
      upstreams.web = {
        servers = {
          "127.0.0.1:8000" = {};
        };
      };
      upstreams.ingest = {
        servers = {
          "127.0.0.1:8001" = {};
        };
      };
      virtualHosts."www.opsgrid.net" = {
        enableACME = true;
        forceSSL = true;
        locations."/assets/" = {
          alias = "/opt/opsgrid-web/assets/";
        };
        locations."/" = {
          proxyPass = "http://web";
        };
      };
      virtualHosts."ingest.opsgrid.net" = {
        enableACME = true;
        forceSSL = true;
        locations."/" = {
          proxyPass = "http://ingest";
        };
      };
      # reject requests with bad host headers
      virtualHosts."_" = {
        onlySSL = true;
        default = true;
        sslCertificate = ./fake-cert.pem;
        sslCertificateKey = ./fake-key.pem;
        extraConfig = "return 444;";
      };
      appendHttpConfig = ''
        error_log stderr;
        access_log syslog:server=unix:/dev/log combined;
      '';
    };

    services.journalbeat = {
      enable = true;
      extraConfig = ''
        journalbeat.inputs:
        - paths: ["/var/log/journal"]
          include_matches: ${(logUnitYaml lib)}
        output:
         elasticsearch:
           hosts: ["https://cloud.humio.com:443/api/v1/ingest/elastic-bulk"]
           username: anything
           password: ${builtins.readFile ../secrets/humiocloud.password}
           compression_level: 5
           bulk_max_size: 200
           worker: 1
           template.enabled: false
      '';
    };

    services.openssh.enable = true;

    services.duplicity = {
      enable = true;
      frequency = "*-*-* 00,12:00:00";
      root = "/tmp/db.backup";
      targetUrl = "pydrive://duply-alpha@repominder.iam.gserviceaccount.com/opsgrid_backups/db";
      secretFile = pkgs.writeText "dupl.env" ''
        GOOGLE_DRIVE_ACCOUNT_KEY="${duplKey}"
      '';
      # https://bugs.launchpad.net/duplicity/+bug/667885
      extraFlags = ["--no-encryption" "--allow-source-mismatch"];
    };
    systemd.services.duplicity = {
      path = [ pkgs.bash pkgs.sqlite ];
      preStart = ''sqlite3 ${dbPath} ".backup /tmp/db.backup"'';
      # privateTmp should handle this, but this helps in case it's eg disabled upstream
      postStop = "rm /tmp/db.backup";
    };


    users = {
      users.root.extraGroups = [ "docker" ];
      users.root.openssh.authorizedKeys.keyFiles = [ ../../.ssh/id_rsa.pub ];
      users.opsgrid-ingest = {
        group = "opsgrid-ingest";
        isSystemUser = true;
        uid = 497;
      };
      groups.opsgrid-ingest ={
        members = [ "opsgrid-ingest" ];
        gid = 499;
      };
      users.opsgrid-web = {
        group = "opsgrid-web";
        isSystemUser = true;
        uid = 500;
      };
      groups.opsgrid-web ={
        members = [ "opsgrid-web" "nginx" ];
        gid = 501;
      };
    };

    networking.firewall.allowedTCPPorts = [ 22 80 443 ];

    security.acme.acceptTerms = true;
    security.acme.email = "domains@simonmweber.com";

    nixpkgs.config = {
      allowUnfree = true;
    };

    environment.systemPackages = with pkgs; [
      curl
      sqlite
      duplicity
      vim
      python3  # for ansible
      htop
      iotop
      sysstat
    ];
  };
in {
  network.description = "opsgrid";
  network.enableRollback = true;
  golf-simon-codes = genericConf;
}
