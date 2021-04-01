{
  golf-simon-codes =
    { config, lib, pkgs, ... }:
    {
      imports = [ ];

      deployment.targetHost = "golf.simon.codes";
      networking.hostName = "golf";
      networking.domain = "simon.codes";
      services.openssh = {
        passwordAuthentication = false;
        challengeResponseAuthentication = false;
        extraConfig = "AllowUsers root";
        permitRootLogin = "yes";
      };

      boot.initrd.availableKernelModules = [ "ata_piix" "uhci_hcd" "virtio_pci" "sr_mod" "virtio_blk" ];
      boot.kernelModules = [ "kvm-amd" ];
      boot.extraModulePackages = [ ];
      boot.loader.grub.device = "/dev/vda";

      fileSystems."/" =
        { device = "/dev/disk/by-uuid/9b9caa88-0a17-4ae5-a92c-c8e61d29b547";
        fsType = "ext4";
      };

      swapDevices =
        [ { device = "/dev/disk/by-uuid/2dbd024d-48a5-4ec8-859b-a331b99fd9f1"; }
      ];

      nix.maxJobs = lib.mkDefault 1;
      virtualisation.hypervGuest.enable = false;
    };
}
