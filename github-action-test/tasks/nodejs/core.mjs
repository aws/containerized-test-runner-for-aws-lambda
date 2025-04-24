export const ping = async (event) => {
    return {
        msg: `pong[${event.msg}]`
    };
};
