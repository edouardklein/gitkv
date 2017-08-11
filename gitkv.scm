(define-module (gitkv)
  #:use-module ((guix licenses) #:prefix license:)
  #:use-module (guix packages)
  #:use-module (guix download)
  #:use-module (guix git-download)
  #:use-module (guix build-system cmake)
  #:use-module (guix build-system python)
  #:use-module (gnu packages curl)
  #:use-module (gnu packages linux)
  #:use-module (gnu packages ssh)
  #:use-module (gnu packages pkg-config)
  #:use-module (gnu packages python)
  #:use-module (gnu packages compression)
  #:use-module (gnu packages tls)
  #:use-module (gnu packages)
  #:use-module (gnu packages version-control))

(define-public libgit2-0.25.0
  (package
    (name "libgit2")
    (version "0.25.0")
    (source (origin
              (method url-fetch)
              (uri (string-append "https://github.com/libgit2/libgit2/"
                                  "archive/v" version ".tar.gz"))
              (file-name (string-append name "-" version ".tar.gz"))
              (sha256
               (base32
                "0yl37h6hsmp8lky74agrl97rqvwni5gisrgrbbjl8rillc8n5ihh"))))
    (build-system cmake-build-system)
    (arguments
     `(#:phases
       (modify-phases %standard-phases
         (add-after 'unpack 'fix-hardcoded-paths
           (lambda _
             (substitute* "tests/repo/init.c"
               (("#!/bin/sh") (string-append "#!" (which "sh"))))
             (substitute* "tests/clar/fs.h"
               (("/bin/cp") (which "cp"))
               (("/bin/rm") (which "rm")))
             #t))
         (add-after 'unpack 'apply-patch
           (lambda* (#:key inputs #:allow-other-keys)
             ;; XXX: For some reason adding the patch in 'patches', which
             ;; leads to a new tarball with all timestamps reset and ordering
             ;; by name (slightly different file order compared to the
             ;; original tarball) leads to an obscure Python error while
             ;; running 'generate.py':
             ;;   'Module' object has no attribute 'callbacks'
             ;; Thus, apply the patch here, which minimizes disruption.
             (let ((patch (assoc-ref inputs "patch")))
               (zero? (system* "patch" "-p1" "--force" "--input" patch)))))
         ;; Run checks more verbosely.
         (replace 'check
           (lambda _ (zero? (system* "./libgit2_clar" "-v" "-Q")))))))
    (inputs
     `(("libssh2" ,libssh2)
       ("libcurl" ,curl)
       ("python" ,python-wrapper)
       ("patch" ,(search-patch "libgit2-use-after-free.patch"))))
    (native-inputs
     `(("pkg-config" ,pkg-config)))
    (propagated-inputs
     ;; These two libraries are in 'Requires.private' in libgit2.pc.
     `(("openssl" ,openssl)
       ("zlib" ,zlib)))
    (home-page "https://libgit2.github.com/")
    (synopsis "Library providing Git core methods")
    (description
     "Libgit2 is a portable, pure C implementation of the Git core methods
provided as a re-entrant linkable library with a solid API, allowing you to
write native speed custom Git applications in any language with bindings.")
    ;; GPLv2 with linking exception
    (license license:gpl2)))


(define-public python-gitkv
  (package
    (name "python-gitkv")
    (version "0.0.5")
  (source (origin
            (method url-fetch)
            (uri (string-append "https://github.com/edouardklein/gitkv/archive/v"
                                version ".tar.gz"))
            (file-name (string-append name "-" version ".tar.gz"))
            (sha256
             (base32
              "use guix download to find the hash"))))
   (build-system python-build-system)
   (arguments
     `(#:phases
       (modify-phases %standard-phases
         (delete 'check)
         (add-after 'install 'test
           (lambda _ (zero? (system* "make" "test")))))))
   (inputs 
      `(("python-coverage" ,python-coverage)
       ("python-flake8" ,python-flake8)
       ("python-sphinx" ,python-sphinx)))    
   (propagated-inputs
     `(("libgit2-0.25.0" ,libgit2-0.25.0)
       ("python-cffi" ,python-cffi)
       ("python-pygit2" ,python-pygit2)
       ("git" ,git)
       ("python" ,python)))

   (home-page "https://github.com/edouardklein/gitkv")
    (synopsis "Use a git repo as a key-value store.")
    (description
     "Use a git repo as a key-value store.")
    ;; GPLv2 with linking exception
    (license license:agpl3)))

(define-public python-gitgv-dev
  (let ((commit "16096072ec5eefcfe04da5c74cd9989ef2852918")
        (revision "1"))
  (package
    (name "python-gitkv-dev")
    (version (string-append "0.0.4-" revision "."
                            (string-take commit 7)))
  (source (origin
            (method git-fetch)
            (uri (git-reference
                  (url "https://github.com/edouardklein/gitkv.git")
                  (commit commit)))
            (file-name (string-append name "-" version "-checkout"))
            (sha256
             (base32
              "05zjqnkc0vgqxvsg8m1v041l0s5mnm1phbghr3wjcl19bkdwfhih"))))
   (build-system python-build-system)
   (arguments
     `(#:phases
       (modify-phases %standard-phases
         (delete 'check)
         (add-after 'install 'test
           (lambda _ (zero? (system* "make" "test")))))))
   (inputs 
      `(("python-coverage" ,python-coverage)
       ("python-flake8" ,python-flake8)
       ("python-sphinx" ,python-sphinx)))    
   (propagated-inputs
     `(("libgit2-0.25.0" ,libgit2-0.25.0)
       ("python-cffi" ,python-cffi)
       ("python-pygit2" ,python-pygit2)
       ("git" ,git)
       ("python" ,python)))

   (home-page "https://github.com/edouardklein/gitkv")
    (synopsis "Use a git repo as a key-value store.")
    (description
     "Use a git repo as a key-value store.")
    ;; GPLv2 with linking exception
    (license license:agpl3))))