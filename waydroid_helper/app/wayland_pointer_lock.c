// #include <gtk/gtk.h>
// #include <gdk/wayland/gdkwayland.h>
// gcc -shared -o libpointer-lock.so -fPIC  pointer-constraints-unstable-v1.c relative-pointer-unstable-v1.c wayland_pointer_lock.c  -lwayland-client -lwayland-server
#include <stdio.h>
#include <string.h>
#include "pointer-constraints-unstable-v1.h"
#include "relative-pointer-unstable-v1.h"
#include "wayland_pointer_lock.h"

static void (*python_relative_motion_callback)(double, double, double, double) = NULL;
static void relative_pointer_handle_relative_motion(void *data,
                                                    struct zwp_relative_pointer_v1 *zwp_relative_pointer_v1,
                                                    uint32_t utime_hi,
                                                    uint32_t utime_lo,
                                                    wl_fixed_t dx,
                                                    wl_fixed_t dy,
                                                    wl_fixed_t dx_unaccel,
                                                    wl_fixed_t dy_unaccel)
{
    double x = wl_fixed_to_double(dx);
    double y = wl_fixed_to_double(dy);
    double x_unaccel = wl_fixed_to_double(dx_unaccel);
    double y_unaccel = wl_fixed_to_double(dy_unaccel);
    if (python_relative_motion_callback)
    {
        python_relative_motion_callback(x, y, x_unaccel, y_unaccel);
    }
}

static const struct zwp_relative_pointer_v1_listener relative_pointer_listener = {
    .relative_motion = relative_pointer_handle_relative_motion,
};

static void seat_handle_capabilities(void *data, struct wl_seat *seat,
                                     enum wl_seat_capability caps)
{

    WaylandData *wd = (WaylandData *)data;
    if ((caps & WL_SEAT_CAPABILITY_POINTER) && !wd->pointer)
    {
        wd->pointer = wl_seat_get_pointer(seat);
        // wl_proxy_set_queue((struct wl_proxy *)wd->pointer, wd->queue);
    }
}

static const struct wl_seat_listener seat_listener = {
    .capabilities = seat_handle_capabilities,
};

static void registry_handle_global(void *data, struct wl_registry *registry,
                                   uint32_t name, const char *interface, uint32_t version)
{
    WaylandData *wd = (WaylandData *)data;
    if (strcmp(interface, wl_compositor_interface.name) == 0)
    {
        wd->compositor = wl_registry_bind(registry, name, &wl_compositor_interface, 1);
        // wl_proxy_set_queue((struct wl_proxy *)wd->compositor, wd->queue);
    }
    else if (strcmp(interface, zwp_pointer_constraints_v1_interface.name) == 0)
    {
        wd->pointer_constraints = wl_registry_bind(registry, name,
                                                   &zwp_pointer_constraints_v1_interface, 1);

        // wl_proxy_set_queue((struct wl_proxy *)wd->pointer_constraints, wd->queue);
    }
    else if (strcmp(interface, wl_seat_interface.name) == 0)
    {
        wd->seat = wl_registry_bind(registry, name, &wl_seat_interface, 1);
        // wl_proxy_set_queue((struct wl_proxy *)wd->seat, wd->queue);
        wl_seat_add_listener(wd->seat, &seat_listener, wd);
    }
    else if (strcmp(interface, zwp_relative_pointer_manager_v1_interface.name) == 0)
    {
        wd->relative_pointer_manager = wl_registry_bind(registry, name,
                                                        &zwp_relative_pointer_manager_v1_interface, 1);

        // wl_proxy_set_queue((struct wl_proxy *)wd->relative_pointer_manager, wd->queue);
    }
}

void unlock_pointer(void *data)
{

    WaylandData *wd = (WaylandData *)data;
    if (wd->locked_pointer)
    {
        zwp_locked_pointer_v1_destroy(wd->locked_pointer);
        wd->locked_pointer = NULL;
    }
    if (wd->relative_pointer)
    {
        zwp_relative_pointer_v1_destroy(wd->relative_pointer);
        wd->relative_pointer = NULL;
    }
    printf("Pointer unlocked and relative pointer disabled\n");
}

bool lock_pointer(void *data)
{
    WaylandData *wd = (WaylandData *)data;
    if (!wd->pointer_constraints || !wd->pointer || !wd->wl_surface)
    {
        fprintf(stderr, "Pointer constraints, pointer, or surface not available\n");
        return false;
    }

    struct wl_region *region = wl_compositor_create_region(wd->compositor);
    wl_region_add(region, 0, 0, INT32_MAX, INT32_MAX);

    wd->locked_pointer = zwp_pointer_constraints_v1_lock_pointer(
        wd->pointer_constraints,
        wd->wl_surface,
        wd->pointer,
        region,
        ZWP_POINTER_CONSTRAINTS_V1_LIFETIME_PERSISTENT);

    wl_region_destroy(region);

    if (!wd->locked_pointer)
    {
        fprintf(stderr, "Failed to lock pointer\n");
        return false;
    }

    if (wd->relative_pointer_manager && wd->pointer)
    {
        wd->relative_pointer = zwp_relative_pointer_manager_v1_get_relative_pointer(
            wd->relative_pointer_manager, wd->pointer);
        // wl_proxy_set_queue((struct wl_proxy *)wd->relative_pointer, wd->queue);
        if (wd->relative_pointer)
        {
            zwp_relative_pointer_v1_add_listener(wd->relative_pointer, &relative_pointer_listener, wd);
        }
        else
        {
            fprintf(stderr, "Failed to create relative pointer\n");
        }
    }

    printf("Pointer locked and relative pointer enabled\n");
    return true;
}

void set_relative_motion_callback(void (*callback)(double, double, double, double))
{
    python_relative_motion_callback = callback;
}

bool wayland_pointer_lock_init(struct wl_display *display, struct wl_surface *surface, void *data)
{
    WaylandData *wd = (WaylandData *)data;
    wd->wl_display = display;
    wd->wl_surface = surface;
    // wd->queue = wl_display_create_queue(display);
    wd->wl_registry = wl_display_get_registry(wd->wl_display);
    if (!wd->wl_registry)
    {
        fprintf(stderr, "Failed to get Wayland registry\n");
        return false;
    }
    // wl_proxy_set_queue((struct wl_proxy *)wd->wl_registry, wd->queue);
    static const struct wl_registry_listener registry_listener = {
        .global = registry_handle_global,
    };
    wl_registry_add_listener(wd->wl_registry, &registry_listener, wd);
    // Make sure registry gets all global callbacks.
    // Implcitly flushes the display
    // wl_display_roundtrip_queue(wd->wl_display, wd->queue);
    // // make sure bound globals received all callbacks
    // wl_display_roundtrip_queue(wd->wl_display, wd->queue);
    wl_display_roundtrip(wd->wl_display);
    wl_display_roundtrip(wd->wl_display);

    if (!wd->pointer_constraints || !wd->seat || !wd->pointer || !wd->relative_pointer_manager)
    {
        fprintf(stderr, "Failed to initialize all required Wayland interfaces\n");
        return false;
    }

    return true;
}
// static void toggle_pointer_lock(GtkWidget *widget, WaylandData *wd)
// {
//     if (wd->locked_pointer)
//     {
//         unlock_pointer(wd);
//         gtk_widget_set_cursor_from_name(widget, "default");
//     }
//     else
//     {
//         lock_pointer(wd);
//         gtk_widget_set_cursor_from_name(widget, "none");
//     }
// }
// static void activate(GtkApplication *app, WaylandData *wd)
// {
//     GtkWidget *window;
//     GtkWidget *button;

//     window = gtk_application_window_new(app);
//     gtk_window_set_title(GTK_WINDOW(window), "Wayland Info");
//     gtk_window_set_default_size(GTK_WINDOW(window), 200, 200);
//     button = gtk_button_new_with_label("Toggle Pointer Lock");
//     g_signal_connect(button, "clicked", G_CALLBACK(toggle_pointer_lock), wd);
//     gtk_window_set_child(GTK_WINDOW(window), button);

//     GdkDisplay *display = gtk_widget_get_display(window);

//     if (GDK_IS_WAYLAND_DISPLAY(display))
//     {
//         wd->wl_display = gdk_wayland_display_get_wl_display(display);
//         printf("wl_display: %p\n", wd->wl_display);
//     }
//     else
//     {
//         printf("Not a Wayland display\n");
//     }

//     // We need to realize the window to get the surface
//     gtk_widget_realize(window);

//     GdkSurface *surface = gtk_native_get_surface(GTK_NATIVE(window));
//     if (GDK_IS_WAYLAND_SURFACE(surface))
//     {
//         wd->wl_surface = gdk_wayland_surface_get_wl_surface(surface);
//         printf("wl_surface: %p\n", wd->wl_surface);
//     }
//     else
//     {
//         printf("Not a Wayland surface\n");
//     }

//     wayland_pointer_lock_init(wd->wl_display, wd->wl_surface, wd);

//     gtk_widget_show(window);
// }

// int main(int argc, char **argv)
// {
//     GtkApplication *app;
//     int status;

//     app = gtk_application_new("org.gtk.example", G_APPLICATION_FLAGS_NONE);
//     WaylandData wd = {0};
//     g_signal_connect(app, "activate", G_CALLBACK(activate), &wd);
//     status = g_application_run(G_APPLICATION(app), argc, argv);
//     g_object_unref(app);

//     return status;
// }