This role makes debian jessie look enough like raspbian-lite that it can be
used as a development environment. We only apply this role if we're not
running on an ARM architecture, as determined by the ansible_architecture
variable.
