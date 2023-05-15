#include "utils.h"

extern ft_global_data_t *global_data;

ft_brute_t * ft_brute_init()
{
    static unsigned int i = 0;
    ft_brute_t *brute = malloc(sizeof(ft_brute_t));
    brute->session = ssh_new();
    if (brute->session == NULL)
    {
        fprintf(stderr, "ERROR: impossibile creare la sessione SSH.\n");
        exit(-1);
    }
    brute->password = ft_fetch_passwd();
    brute->coro = ft_async_new();
    brute->id = ++i;
    // temp var
    brute->same_sess = 0;
    return brute;
}

ft_list_t * ft_list_init()
{
    ft_list_t *list = malloc(sizeof(ft_list_t));
    list->data = ft_brute_init();
    list->next = NULL;
    return list;
}

ft_list_coordinator_t * ft_coordinator_init()
{
    ft_list_coordinator_t *coordinator = malloc(sizeof(ft_list_coordinator_t));
    if (!coordinator)
    {
        perror("ERROR: impossibile allocare memoria per la lista dei coordinatori.\n");
        exit(EXIT_FAILURE);
    }
    coordinator->head = NULL;
    coordinator->tail = NULL;
    coordinator->size = 0;
    return coordinator;
}

void ft_brute_free(ft_brute_t *brute)
{
    if (!brute)
        return;
    // if (brute->password)
        free(brute->password);
    ssh_disconnect(brute->session);
    ssh_free(brute->session);
    free(brute);
}

void ft_list_free(ft_list_t *list)
{
    ft_brute_free(list->data);
    free(list);
}

void ft_coordinator_free(ft_list_coordinator_t *coordinator)
{
    ft_list_t *tmp = coordinator->head;
    while (tmp != NULL)
    {
        ft_list_t *next = tmp->next;
        ft_list_free(tmp);
        tmp = next;
    }
    free(coordinator);
}

ft_brute_t* ft_fetch_session(ft_list_coordinator_t *coordinator)
{
    if ((coordinator->size - global_data->MAX_SESSION) & (1 << 31))
    {
        ft_list_t *new = ft_list_init();
        if (!new->data->password)
        {
            ft_list_free(new);
            return ft_list_fetch(coordinator);
        }
        if (coordinator->head == NULL)
            coordinator->head = new;
        else
            coordinator->tail->next = new;
        coordinator->tail = new;
        ++coordinator->size;
    }
    return ft_list_fetch(coordinator);
}

ft_brute_t* ft_list_fetch(ft_list_coordinator_t *coordinator)
{
    ft_list_t *tmp = coordinator->head;
    while (tmp && tmp->data->to_delete)
    {
        coordinator->head = coordinator->head->next;
        ft_list_free(tmp);
        --coordinator->size;
        tmp = coordinator->head;
    }
    if (coordinator->head && coordinator->head->next)
    {
        coordinator->head = coordinator->head->next;
        coordinator->tail->next = tmp;
        coordinator->tail = tmp;
        coordinator->tail->next = NULL;
    }
    if (tmp && tmp->data)
        return tmp->data;
    return NULL;
}

void ft_update_password(ft_list_coordinator_t *coordinator, ft_brute_t *data)
{
    free(data->password);
    data->password = ft_fetch_passwd();
    
    if (data->password == NULL)
        data->to_delete = 1;
    // temp istr
    else
        ++data->same_sess;
}

char *ft_fetch_passwd()
{
    static int status = 0;
    static int fd;
    static struct stat sb;
    static char *file_data, *start;
    static size_t len;

    char *line, *newline;
    switch (status)
    {
        case 0:
            fd = open(global_data->filename, O_RDONLY);
            if (fd == -1) {
                perror("open");
                exit(EXIT_FAILURE);
            }

            // ottieni le informazioni sul file
            if (fstat(fd, &sb) == -1) {
                perror("fstat");
                exit(EXIT_FAILURE);
            }
            
            // mappa il file in memoria
            len = sb.st_size;
            file_data = start = mmap(NULL, sb.st_size, PROT_READ, MAP_PRIVATE, fd, 0);
            if (file_data == MAP_FAILED) {
                perror("mmap");
                exit(EXIT_FAILURE);
            }
            status = 1;
        case 1:
            // leggi il file riga per riga utilizzando getline()
            newline = memchr(start, '\n', len);
            if (!newline)
            {
                newline = start + len;
                status = 2;
            }
            int line_len = newline - start;
            char *line = malloc(line_len + 1);
            memcpy(line, start, line_len);
            line[line_len] = '\0';
            start = newline + 1;
            len -= line_len + 1;
            return line;
        case 2:
            // dealloca la memoria mappata
            if (munmap(file_data, sb.st_size) == -1)
            {
                perror("munmap");
                exit(EXIT_FAILURE);
            }
            
            // chiudi il file
            if (close(fd) == -1)
            {
                perror("close");
                exit(EXIT_FAILURE);
            }
            status = 3;
        case 3:
            return NULL;
        default:
            return NULL;
    }
}

void ft_fast_recovery(ft_brute_t *data)
{
    // printf("In fast recovery\n");
    ssh_disconnect(data->session);
    ssh_free(data->session);
    ft_set_async_status(&data->coro, ASYNC_INIT);
    data->session = ssh_new();
    if (data->session == NULL)
    {
        fprintf(stderr, "ERROR: impossibile creare la sessione SSH.\n");
        exit(-1);
    }
    // temp var
    data->same_sess = 0;
}