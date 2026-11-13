# Notice

This repository is a customised fork of [Keshif+](https://github.com/keshifme/keshif-plus),
Copyright (c) 2023, Keshif LLC. It is not an official Keshif release and is not
endorsed by Keshif LLC or its contributors.

## Licence

- The upstream `LICENSE` file, kept unchanged, is the **BSD 3-Clause** licence.
- Upstream's `package.json` (revision `f534314`) declares `"license": "AGPL-3.0-only"`.
  The two statements conflict, and only the copyright holder can resolve that.

This fork is distributed in a way that meets both readings:

- the copyright notice and licence text are kept, here and in every distributed copy of `dist/`;
- the complete readable source of every modification (`dist/keshif.js`, with its history)
  is publicly available in this repository;
- the names of Keshif LLC and its contributors are not used to promote derived products.

Modifications made in this fork are offered under the same BSD 3-Clause terms as the
upstream `LICENSE`. Projects that redistribute `dist/` must ship `LICENSE` and this `NOTICE.md`
with it.

## Bundled third-party code

`dist/vendor.js` and `dist/vendor_mapping.js` bundle third-party libraries under their own
licences, including D3 (ISC), Leaflet (BSD-2-Clause), Supercluster (ISC), DOMPurify
(Apache-2.0 / MPL-2.0), Popper (MIT), Tippy (MIT), noUiSlider (MIT), Luxon (MIT), Pikaday (MIT)
and PapaParse (MIT). `dist/keshif.css` and `dist/assets/fa-*` contain Font Awesome 6 **Free**
(icons CC BY 4.0, fonts SIL OFL 1.1, code MIT). Their in-source notices are retained.
