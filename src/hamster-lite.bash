# bash completion for hamsterlite

_hamster-lite_helper()
{
    local IFS=$'\n'
    COMPREPLY+=( $(
        hamster "$@" 2>/dev/null ) )
}

_hamster-lite()
{
    local cur prev opts base
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    #
    #  The basic options we'll complete.
    #
    opts="activities categories current export list search start stop "


    #
    #  Complete the arguments to some of the basic commands.
    #
    case "${prev}" in

    start|export)
        _hamster-lite_helper "assist" "$prev" "$cur"
        return 0
        ;;

    esac

   COMPREPLY=($(compgen -W "${opts}" -- ${cur}))
   return 0
}
complete -F _hamster-lite hamster-lite
