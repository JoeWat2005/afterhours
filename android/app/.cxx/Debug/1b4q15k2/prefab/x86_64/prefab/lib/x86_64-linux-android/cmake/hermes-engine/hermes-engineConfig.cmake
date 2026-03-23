if(NOT TARGET hermes-engine::hermesvm)
add_library(hermes-engine::hermesvm SHARED IMPORTED)
set_target_properties(hermes-engine::hermesvm PROPERTIES
    IMPORTED_LOCATION "C:/Users/Joseph/.gradle/caches/9.0.0/transforms/b739796ac83c2fb75564bd4419450739/transformed/hermes-android-0.14.1-debug/prefab/modules/hermesvm/libs/android.x86_64/libhermesvm.so"
    INTERFACE_INCLUDE_DIRECTORIES "C:/Users/Joseph/.gradle/caches/9.0.0/transforms/b739796ac83c2fb75564bd4419450739/transformed/hermes-android-0.14.1-debug/prefab/modules/hermesvm/include"
    INTERFACE_LINK_LIBRARIES ""
)
endif()

