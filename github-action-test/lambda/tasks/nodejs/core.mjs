export const ping = async (event) => {
    return {
        msg: `pong[${event.msg}]`
    };
};

export const echoClientContextCustom = async (_event, context) => {
    return { custom: context.clientContext?.custom ?? null };
};
