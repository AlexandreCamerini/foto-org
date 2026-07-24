import { useInfiniteQuery } from "@tanstack/react-query";
import { useMemo } from "react";

import { api, type FiltrosMidia } from "../api";

const PAGINA = 200;

/** Query paginada da grade — grade e loupe compartilham o mesmo cache. */
export function useMidia(filtros: FiltrosMidia) {
  const query = useInfiniteQuery({
    queryKey: ["midia", filtros],
    queryFn: ({ pageParam }) => api.midia(filtros, pageParam, PAGINA),
    initialPageParam: 0,
    getNextPageParam: (ultima) => {
      const proximo = ultima.offset + ultima.itens.length;
      return proximo < ultima.total ? proximo : undefined;
    },
  });

  const itens = useMemo(
    () => (query.data?.pages ?? []).flatMap((p) => p.itens),
    [query.data],
  );
  const total = query.data?.pages[0]?.total ?? 0;

  return { ...query, itens, total };
}

export type MidiaQuery = ReturnType<typeof useMidia>;
