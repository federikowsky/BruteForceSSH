#ifndef __UTILS_H__
#define __UTILS_H__

#include <libft/libft.h>
#include <libssh/libssh.h>
#include <sys/stat.h>

#define POS 10

typedef struct session
{
    ssh_session session;
    struct async coro;
    char *password;
    unsigned int id;
    unsigned int to_delete;
    unsigned int same_sess;
} ft_brute_t;

typedef struct linkedlist {
    ft_brute_t *data;
    struct list *next;
} ft_list_t;

typedef struct coordinatorlist {
    ft_list_t *head;
    ft_list_t *tail;
    int size;
} ft_list_coordinator_t;

typedef struct global {
    time_t startTime, endTime, elapsedTime;
    struct tm * timeinfo;
    char *filename;
    char *host;
    char *username;
    unsigned long long pass_tried;
    unsigned int MAX_SESSION;
    int verbose;
    int done;
    unsigned short port;
} ft_global_data_t;


ft_brute_t * ft_brute_init();
ft_list_t * ft_list_init();
ft_list_coordinator_t * ft_coordinator_init();
ft_brute_t* ft_fetch_session(ft_list_coordinator_t *coordinator);
ft_brute_t* ft_list_fetch(ft_list_coordinator_t *coordinator);
void ft_update_password(ft_list_coordinator_t *coordinator, ft_brute_t *data);
char *ft_fetch_passwd();
void ft_fast_recovery(ft_brute_t *data);
void ft_brute_free(ft_brute_t *brute);
void ft_list_free(ft_list_t *list);
void ft_coordinator_free(ft_list_coordinator_t *coordinator);
#endif