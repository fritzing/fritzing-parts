This repository contains all part definitions that are shipped with the [fritzing app](https://github.com/fritzing/fritzing-app). Every fritzing installation contains a clone of this repository and is continuously updated through github, so take great care when making changes.

Parts are composed of meta-data (.fzp) and related graphics (.svg). Read more on the [part folder structure and file format](https://github.com/fritzing/fritzing-app/wiki/2.1-Part-file-format).

## Contributing parts

See the [contribution guidelines](https://github.com/fritzing/fritzing-parts/blob/master/CONTRIBUTING.md) on how to contribute directly to this repository. If this seems too complex, you may alternatively sare your part in the [fritzing forum](http://forum.fritzing.org/c/parts-submit).

## Creating parts

Learn [how to create custom parts](http://fritzing.org/learning/tutorials/creating-custom-parts/)

## Parts API

The fritzing-parts repository contains a [`gh-pages`](github.com/fritzing/fritzing-parts/tree/gh-pages) branch to bring up a small http api. Pay attention that the response `Content-Type` is not the correct one. The jekyll server running at Github ignore the `webrick headers` setting from the `_config.yml`.  
The following routes are available:

#### GET [/](`https://fritzing.github.io/fritzing-parts/`)
return some metadata about the fritzing-parts api

#### GET [/fzb](`https://fritzing.github.io/fritzing-parts/fzb`)
return an object of all `*.fzb` files

#### GET [/fzp](`https://fritzing.github.io/fritzing-parts/fzp`)
return an object of all `*.fzp` files

#### GET [/fzp/core](`https://fritzing.github.io/fritzing-parts/fzp/core`)
return an object of all `core/*.fzp` files

#### GET [/fzp/obsolete](`https://fritzing.github.io/fritzing-parts/fzp/obsolete`)
return an object of all `obsolete/*.fzp` files

---

There is a work in progress swagger specification which can be surfed at https://editor.swagger.io/#/?import=https://fritzing.github.io/fritzing-parts/api/swagger.yaml
