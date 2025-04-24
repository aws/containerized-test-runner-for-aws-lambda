export const handler = async (event, context) => {
    return {
        msg: `pong[${event.msg}]`
    };
};
