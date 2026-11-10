## START: Set by rpmautospec
## (rpmautospec version 0.8.3)
## RPMAUTOSPEC: autorelease, autochangelog
%define autorelease(e:s:pb:n) %{?-p:0.}%{lua:
    release_number = 9;
    base_release_number = tonumber(rpm.expand("%{?-b*}%{!?-b:1}"));
    print(release_number + base_release_number - 1);
}%{?-e:.%{-e*}}%{?-s:.%{-s*}}%{!?-n:%{?dist}}
## END: Set by rpmautospec

Name:           plocate
Version:        1.1.22
# Last release in Fedora was 3.  Therefore, let's use 3 to continue that
# sequence seamlessly.
Release:        %autorelease -b 3
Summary:        Much faster locate

# Licensing information taken from README:
# * plocate (except updatedb) - GPL-2.0-or-later
# * updatedb                  - GPL-2.0-only
License:        GPL-2.0-or-later AND GPL-2.0-only
URL:            https://plocate.sesse.net/
Source0:        https://plocate.sesse.net/download/plocate-%{version}.tar.gz
Source1:        plocate.sysusers
Source2:        plocate.tmpfiles

Patch1:         0001-Avoid-writing-uninitialized-header-data.patch
Patch2:         0002-Don-t-leak-file-descriptor.patch
Patch3:         0003-Reset-string-explicitely-to-prevent-undefined-behavi.patch

BuildRequires:  meson
BuildRequires:  gcc-c++
BuildRequires:  systemd-rpm-macros
BuildRequires:  pkgconfig(liburing)
BuildRequires:  pkgconfig(libzstd)
BuildRequires:  libatomic
Requires(post): systemd-tmpfiles

# The plan is to provide both mlocate and plocate for one or two
# Fedora releases, and then retire mlocate when the bugs in plocate
# have been ironed out. Thus, we only allow one or the other to be
# installed.
Conflicts:      mlocate
Provides:       locate

# https://bugzilla.redhat.com/show_bug.cgi?id=2052433
Obsoletes:      mlocate < 0.26-500

%description
plocate is a locate(1) based on posting lists, giving much faster
searches on a much smaller index. It is a drop-in replacement for
mlocate in nearly all aspects, and is fast on SSDs and non-SSDs alike.

%prep
%autosetup -p1

%build
%meson -Dsystemunitdir=%_unitdir -Dinstall_systemd=true
%meson_build

# Man page alias
cat >locate.1 <<EOF
.so man1/plocate.1
EOF

cat >updatedb.conf <<EOF
# https://bugzilla.redhat.com/show_bug.cgi?id=2033216
PRUNEFS = "9p afs autofs binfmt_misc ceph cgroup cgroup2 cifs coda configfs curlftpfs debugfs devfs devpts devtmpfs ecryptfs ftpfs fuse.ceph fuse.cryfs fuse.encfs fuse.glusterfs fuse.gvfsd-fuse fuse.mfs fuse.rclone fuse.rozofs fuse.sshfs fusec fusesmb gfs gfs2 gpfs hugetlbfs iso9660 lustre lustre_lite mfs mqueue ncpfs nfs nfs4 ocfs ocfs2 proc pstore ramfs pstorefs rootfs rpc_pipefs securityfs smbfs sysfs tmpfs tracefs udev udf usbfs"
# https://bugzilla.redhat.com/show_bug.cgi?id=2097889
PRUNEPATHS = "/tmp /media /dev /sys /proc /run /var/cache /var/spool"
EOF

%install
%meson_install

install -p -D -m 0644 %{SOURCE1} %{buildroot}%{_sysusersdir}/plocate.conf
install -p -D -m 0644 %{SOURCE2} %{buildroot}%{_tmpfilesdir}/plocate.conf
# Let tmpfiles create the state directory at install/boot time.
rm -rf %{buildroot}%{_sharedstatedir}/plocate
ln -s plocate %{buildroot}%{_bindir}/locate
install -p -D -m 0644 -t %{buildroot}%{_mandir}/man1/ locate.1
install -p -D -m 0644 -t %{buildroot}%{_sysconfdir}/ updatedb.conf

# A state file to carry information from %%post to %%posttrans. See
# https://docs.fedoraproject.org/en-US/packaging-guidelines/Scriptlets/#_saving_state_between_scriptlets.
%global plocate_start_now %{_localstatedir}/lib/rpm-state/plocate_start_now

%pre
%sysusers_create_compat %{SOURCE1}

%post
%systemd_post plocate-updatedb.service plocate-updatedb.timer
%tmpfiles_create %{_tmpfilesdir}/plocate.conf

if [ $1 == 1 ] && [ -d /run/systemd ]; then
     touch %{plocate_start_now} || :
fi

%preun
%systemd_preun plocate-updatedb.service plocate-updatedb.timer

%postun
%systemd_postun_with_restart plocate-updatedb.service plocate-updatedb.timer

%posttrans
# The timer runs once per day. On new installs, let's start both the
# timer and the service immediately in the background, so that the db
# becomes populated. When people install this package onto a running
# system, it's reasonable to assume that they want to use the database.
if [ -f %{plocate_start_now} ]; then
   rm %{plocate_start_now} || :
   if systemctl is-enabled plocate-updatedb.timer &>/dev/null; then
      systemctl start --no-block plocate-updatedb.timer plocate-updatedb.service || :
   fi
fi

%files
%license COPYING
%doc README
%attr(02755,-,plocate) %_bindir/plocate
%_bindir/locate
%_sbindir/plocate-build
%_sbindir/updatedb
%_unitdir/plocate-updatedb.service
%_unitdir/plocate-updatedb.timer
%_mandir/man1/plocate.1*
%_mandir/man1/locate.1*
%_mandir/man5/updatedb.conf.5*
%_mandir/man8/plocate-build.8*
%_mandir/man8/updatedb.8*
%_sysusersdir/plocate.conf
%{_tmpfilesdir}/plocate.conf
%config(noreplace) %{_sysconfdir}/updatedb.conf
%ghost %attr(0755,root,root) %dir %{_sharedstatedir}/plocate
%ghost %attr(0644,root,root) %{_sharedstatedir}/plocate/CACHEDIR.TAG
%ghost %attr(0640,-,plocate) %verify(not md5 mtime) %{_sharedstatedir}/plocate/plocate.db

%changelog
## START: Generated by rpmautospec
* Wed Apr 08 2026 Michal Sekletar <msekleta@redhat.com> - 1.1.22-11
- Migrate to systemd-tmpfiles

* Fri Feb 14 2025 Michal Sekletar <msekleta@redhat.com> - 1.1.22-10
- Fix SAST issues (RHEL-39394)

* Tue Oct 29 2024 Troy Dawson <tdawson@redhat.com> - 1.1.22-9
- Bump release for October 2024 mass rebuild:

* Tue Aug 20 2024 Michal Sekletar <msekleta@redhat.com> - 1.1.22-8
- Initialize fmf

* Tue Aug 20 2024 Michal Sekletar <msekleta@redhat.com> - 1.1.22-7
- Add ci.fmf

* Mon Aug 12 2024 Michal Sekletar <msekleta@redhat.com> - 1.1.22-6
- Add gating configuration

* Mon Jun 24 2024 Troy Dawson <tdawson@redhat.com> - 1.1.22-5
- Bump release for June 2024 mass rebuild

* Thu May 23 2024 Lukáš Zaoral <lzaoral@redhat.com> - 1.1.22-4
- spec: fix autorelease to be consistent with the base SRPM taken from
  Fedora ELN.

* Thu May 16 2024 Lukáš Zaoral <lzaoral@redhat.com> - 1.1.22-3
- migrate to SPDX license format

* Thu Jan 25 2024 Fedora Release Engineering <releng@fedoraproject.org> - 1.1.22-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_40_Mass_Rebuild

* Mon Jan 22 2024 Zbigniew Jędrzejewski-Szmek <zbyszek@in.waw.pl> - 1.1.22-1
- Version 1.1.22 (rhbz#2259687)

* Sun Jan 21 2024 Fedora Release Engineering <releng@fedoraproject.org> - 1.1.17-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_40_Mass_Rebuild

* Fri Jul 21 2023 Fedora Release Engineering <releng@fedoraproject.org> - 1.1.17-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_39_Mass_Rebuild

* Fri Jan 20 2023 Fedora Release Engineering <releng@fedoraproject.org> - 1.1.17-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_38_Mass_Rebuild

* Tue Dec 27 2022 Zbigniew Jędrzejewski-Szmek <zbyszek@in.waw.pl> - 1.1.17-1
- Version 1.1.17
- Bump Obsoletes for cover mlocate in F37 and F38.

* Wed Aug 17 2022 Zbigniew Jędrzejewski-Szmek <zbyszek@in.waw.pl> - 1.1.16-3
- Update default config to use the defaults in Debian

* Wed Aug 17 2022 Zbigniew Jędrzejewski-Szmek <zbyszek@in.waw.pl> - 1.1.16-2
- Ignore caches and ephemeral file system types (rhbz#2033216,
  rhbz#2097889)

* Wed Aug 17 2022 Zbigniew Jędrzejewski-Szmek <zbyszek@in.waw.pl> - 1.1.16-1
- Version 1.1.16

* Fri Jul 22 2022 Fedora Release Engineering <releng@fedoraproject.org> - 1.1.15-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_37_Mass_Rebuild

* Sun Mar 06 2022 Zbigniew Jędrzejewski-Szmek <zbyszek@in.waw.pl> - 1.1.15-3
- Add Obsoletes for mlocate versions in F35- (for #2052433)

* Sat Feb 19 2022 Zbigniew Jędrzejewski-Szmek <zbyszek@in.waw.pl> - 1.1.15-2
- Add virtual Provides:locate to make upgrades easier (rhbz#2052433)

* Sat Feb 19 2022 Zbigniew Jędrzejewski-Szmek <zbyszek@in.waw.pl> - 1.1.15-1
- Version 1.1.15

* Fri Jan 21 2022 Fedora Release Engineering <releng@fedoraproject.org> - 1.1.13-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_36_Mass_Rebuild

* Fri Nov 26 2021 Zbigniew Jędrzejewski-Szmek <zbyszek@in.waw.pl> - 1.1.13-4
- Fix mode in %%ghost line

* Wed Nov 24 2021 Zbigniew Jędrzejewski-Szmek <zbyszek@in.waw.pl> - 1.1.13-3
- Add %%ghost for /etc/updatedb.conf

* Wed Nov 24 2021 Zbigniew Jędrzejewski-Szmek <zbyszek@in.waw.pl> - 1.1.13-2
- Add locate(1) man page alias

* Wed Nov 24 2021 Zbigniew Jędrzejewski-Szmek <zbyszek@in.waw.pl> - 1.1.13-1
- Version 1.1.13

* Fri Oct 29 2021 Zbigniew Jędrzejewski-Szmek <zbyszek@in.waw.pl> - 1.1.12-2
- Remove plocate.db when the package is removed

* Fri Oct 29 2021 Zbigniew Jędrzejewski-Szmek <zbyszek@in.waw.pl> - 1.1.12-1
- Version 1.1.12

* Tue Sep 14 2021 Zbigniew Jędrzejewski-Szmek <zbyszek@in.waw.pl> - 1.1.11-2
- Upload sources

* Wed Sep 08 2021 Zbigniew Jędrzejewski-Szmek <zbyszek@in.waw.pl> - 1.1.11-1
- Version 1.1.11

* Mon Jun 21 2021 Zbigniew Jędrzejewski-Szmek <zbyszek@in.waw.pl> - 1.1.8-1
- Update to latest version

* Wed May 12 2021 Zbigniew Jędrzejewski-Szmek <zbyszek@in.waw.pl> - 1.1.7-1
- Resolve comments from initial review
- Start the service and timer in %%posttrans
- Conflict with mlocate and provide /bin/locate alias

* Fri Feb 19 2021 Zbigniew Jędrzejewski-Szmek <zbyszek@in.waw.pl> - 1.1.4-1
- First version

## END: Generated by rpmautospec
